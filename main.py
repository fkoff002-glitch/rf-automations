import os
import re
import ipaddress
import logging
import tempfile
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator

# ---------------------------------------------------------
# CONFIGURATION & LOGGING
# ---------------------------------------------------------
DATA_SOURCE_URL = "https://fkoff002-glitch.github.io/RF-DATA/inventory.csv"
# Allow frontend to communicate
FRONTEND_URL = "https://fkoff002-glitch.github.io"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - NOC-AUTOMATION - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="NOC RF Automation Backend")

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# DATA MODELS
# ---------------------------------------------------------

class PingResult(BaseModel):
    level: str  # client, base, gateway
    ip: str
    status: str  # UP, DOWN
    packet_loss: str
    avg_latency_ms: Optional[float]

class BTSPopResult(BaseModel):
    base_ip: str
    status: str

class LoopbackResult(BaseModel):
    ip: str
    status: str

class DiagnosisResponse(BaseModel):
    parallel_check: List[PingResult]
    bts_pop_scan: List[BTSPopResult]
    loopback: Optional[LoopbackResult]
    final_status: str
    root_cause_level: str

# ---------------------------------------------------------
# INVENTORY MANAGEMENT (In-Memory)
# ---------------------------------------------------------
inventory_cache = []
inventory_index = {} # Lookup by client, bts, pop, ip

def validate_ip(ip: str) -> bool:
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

async def fetch_inventory():
    global inventory_cache, inventory_index
    logger.info("Fetching inventory from GitHub...")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(DATA_SOURCE_URL)
            resp.raise_for_status()
            
            # Parse CSV (Assuming headers: client, bts, pop, client_ip, base_ip, loopback_ip)
            # Adjust parsing based on actual CSV format if headers differ
            lines = resp.text.splitlines()
            headers = [h.strip().lower() for h in lines[0].split(',')]
            
            inventory_cache = []
            inventory_index = {
                "client": {}, "bts": {}, "pop": {}, "ip": {}
            }
            
            for line in lines[1:]:
                if not line.strip(): continue
                values = [v.strip() for v in line.split(',')]
                item = dict(zip(headers, values))
                
                # Validation
                if not all(k in item for k in ['client_ip', 'base_ip']):
                    continue
                
                # Structure
                record = {
                    "client": item.get('client', 'Unknown'),
                    "bts": item.get('bts', 'Unknown'),
                    "pop": item.get('pop', 'Unknown'),
                    "client_ip": item['client_ip'],
                    "base_ip": item['base_ip'],
                    "loopback_ip": item.get('loopback_ip') # Optional
                }
                
                inventory_cache.append(record)
                
                # Indexing for fast search
                inventory_index["client"][record["client"].lower()] = record
                inventory_index["bts"][record["bts"].lower()] = record # Returns first match
                inventory_index["pop"][record["pop"].lower()] = record  # Returns first match
                inventory_index["ip"][record["client_ip"]] = record
                inventory_index["ip"][record["base_ip"]] = record

            logger.info(f"Inventory loaded: {len(inventory_cache)} records.")

    except Exception as e:
        logger.error(f"Failed to load inventory: {e}")

@app.on_event("startup")
async def startup_event():
    await fetch_inventory()

# ---------------------------------------------------------
# NETWORK LOGIC (FPING & PING)
# ---------------------------------------------------------

def calculate_gateway(base_ip: str) -> str:
    """Gateway is always Base_IP - 1"""
    try:
        ip_obj = ipaddress.ip_address(base_ip)
        # Subtract 1. Handle /29 network logic implicitly
        gateway = ipaddress.ip_address(int(ip_obj) - 1)
        return str(gateway)
    except Exception:
        return "0.0.0.0"

def parse_fping_output(output: str) -> Dict[str, dict]:
    """
    Parses fping output.
    Returns: { 'ip': { 'sent': int, 'received': int, 'loss': int, 'avg': float } }
    """
    results = {}
    # Regex for fping -l output:
    # x.x.x.x : [0-9]+ transmitted, [0-9]+ received, [0-9]+% loss, min/avg/max = ...
    # OR
    # x.x.x.x is unreachable
    
    # Example line: 10.10.10.1 : 10 transmitted, 10 received, 0% loss, min/avg/max = 1.2/2.3/5.4 ms
    pattern_stats = re.compile(
        r'(?P<ip>\d+\.\d+\.\d+\.\d+)\s*:\s*'
        r'(?P<sent>\d+)\s*transmitted,\s*'
        r'(?P<received>\d+)\s*received,\s*'
        r'(?P<loss>\d+)%\s*loss.*'
        r'min/avg/max\s*=\s*[\d.]+/(?P<avg>[\d.]+)/[\d.]+'
    )
    
    pattern_unreachable = re.compile(
        r'(?P<ip>\d+\.\d+\.\d+\.\d+)\s+is\s+unreachable'
    )
    
    for line in output.splitlines():
        match = pattern_stats.match(line)
        if match:
            results[match.group('ip')] = {
                "sent": int(match.group('sent')),
                "received": int(match.group('received')),
                "loss": int(match.group('loss')),
                "avg": float(match.group('avg'))
            }
            continue
            
        match = pattern_unreachable.match(line)
        if match:
            results[match.group('ip')] = {
                "sent": 0, # Assuming fping default count or immediate failure
                "received": 0,
                "loss": 100,
                "avg": None
            }
            
    return results

async def run_fping_batch(targets: List[str]) -> Dict[str, dict]:
    """
    Creates temp file, runs fping, parses output, cleans up.
    Security: No shell=True. Validates IPs before writing.
    """
    # Validate IPs
    valid_targets = [t for t in targets if validate_ip(t)]
    if not valid_targets:
        return {}

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        temp_filename = f.name
        f.write("\n".join(valid_targets))

    try:
        # Command: fping -l -f <file>
        # -l: loop/stats
        # -f: read from file
        # -c 3: send 3 packets (good for quick diag)
        # Note: fping default count is usually 1 or infinite depending on version. 
        # We specify -c 3 for reliable loss % calculation.
        process = await asyncio.create_subprocess_exec(
            'fping', '-l', '-c', '3', '-f', temp_filename,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        output = stdout.decode('utf-8')
        return parse_fping_output(output)
    finally:
        # Security: Auto-delete
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

async def run_single_ping(ip: str) -> dict:
    """Standard ping for Loopback if preferred, or re-use fping."""
    # Using fping for consistency with stats, but treating it as a single check
    res = await run_fping_batch([ip])
    return res.get(ip, {"sent": 0, "received": 0, "loss": 100, "avg": None})

# ---------------------------------------------------------
# DIAGNOSIS ENDPOINT
# ---------------------------------------------------------

# Basic In-memory Rate Limiter
rate_limit_store = {}

@app.post("/api/diagnose", response_model=DiagnosisResponse)
async def diagnose_link(search_query: str = Query(..., description="Client Name, BTS, POP, or IP")):
    """Performs the strict 3-step RF diagnosis."""
    
    # 1. Rate Limiting Check
    now = datetime.now().timestamp()
    if search_query in rate_limit_store:
        if now - rate_limit_store[search_query] < 2: # Max 1 request per 2 sec per target
            raise HTTPException(status_code=429, detail="Too many requests. Please wait.")
    rate_limit_store[search_query] = now

    # 2. Search Inventory
    query = search_query.lower().strip()
    target_record = None
    
    # Search strategy
    if query in inventory_index["client"]: target_record = inventory_index["client"][query]
    elif query in inventory_index["ip"]: target_record = inventory_index["ip"][query]
    elif query in inventory_index["bts"]: target_record = inventory_index["bts"][query] # Hits first client in BTS
    elif query in inventory_index["pop"]: target_record = inventory_index["pop"][query] # Hits first client in POP
    
    if not target_record:
        raise HTTPException(status_code=404, detail="Target not found in RF Inventory.")

    logger.info(f"Diagnosis started for: {target_record['client']} ({search_query})")

    # ------------------------------------------------------
    # STEP 1: CLIENT + BASE + GATEWAY PARALLEL CHECK
    # ------------------------------------------------------
    gateway_ip = calculate_gateway(target_record['base_ip'])
    
    targets_step1 = [
        target_record['client_ip'],
        target_record['base_ip'],
        gateway_ip
    ]
    
    # Execute Step 1
    step1_results_raw = await run_fping_batch(targets_step1)
    
    # Map results to levels
    def get_stat(ip):
        return step1_results_raw.get(ip, {"sent":0, "received":0, "loss":100, "avg":None})

    client_stat = get_stat(target_record['client_ip'])
    base_stat = get_stat(target_record['base_ip'])
    gateway_stat = get_stat(gateway_ip)

    parallel_check_response = [
        PingResult(level="client", ip=target_record['client_ip'], 
                   status="UP" if client_stat['loss'] < 100 else "DOWN", 
                   packet_loss=f"{client_stat['loss']}%", avg_latency_ms=client_stat['avg']),
        PingResult(level="base", ip=target_record['base_ip'], 
                   status="UP" if base_stat['loss'] < 100 else "DOWN", 
                   packet_loss=f"{base_stat['loss']}%", avg_latency_ms=base_stat['avg']),
        PingResult(level="gateway", ip=gateway_ip, 
                   status="UP" if gateway_stat['loss'] < 100 else "DOWN", 
                   packet_loss=f"{gateway_stat['loss']}%", avg_latency_ms=gateway_stat['avg'])
    ]

    # DECISION LOGIC STEP 1
    if client_stat['loss'] < 100:
        logger.info(f"Result: LINK UP - {target_record['client_ip']} reachable")
        return DiagnosisResponse(
            parallel_check=parallel_check_response,
            bts_pop_scan=[],
            loopback=None,
            final_status="LINK UP – Client Reachable",
            root_cause_level="client"
        )

    if client_stat['loss'] == 100 and base_stat['loss'] < 100:
        logger.warning(f"Result: FAULT - Client Radio/CPE Down")
        return DiagnosisResponse(
            parallel_check=parallel_check_response,
            bts_pop_scan=[],
            loopback=None,
            final_status="FAULT – Client Radio / CPE Down",
            root_cause_level="client"
        )

    # If Client Down AND Base Down:
    # Check Gateway. If Gateway is DOWN, it implies bigger issue, but we follow strict flow:
    # "If Client DOWN and Base DOWN but Gateway UP -> PROCEED"
    if gateway_stat['loss'] == 100:
        # Gateway is also down. Logic dictates if base is down, gateway is likely down (Base-1).
        # However, strict flow says: "If Client DOWN and Base DOWN but Gateway UP".
        # If Gateway is down, we technically skip "Sector Issue" and likely go straight to BTS check or Loopback?
        # Logic interpretation: If Base is down, the sector is suspect.
        # Let's assume we proceed to BTS check if Base is down.
        pass

    # ------------------------------------------------------
    # STEP 2: BTS / POP MASS BASE CHECK
    # ------------------------------------------------------
    # Find all bases in this BTS/POP
    site_bts = target_record.get('bts')
    site_pop = target_record.get('pop')
    
    related_bases = []
    # Filter inventory for all records matching this BTS or POP
    for item in inventory_cache:
        if item.get('bts') == site_bts or item.get('pop') == site_pop:
            related_bases.append(item['base_ip'])
    
    # Deduplicate
    related_bases = list(set(related_bases))
    
    logger.info(f"Step 2: Checking {len(related_bases)} bases at {site_bts}/{site_pop}")
    
    step2_results_raw = await run_fping_batch(related_bases)
    
    bts_pop_response = []
    any_base_up = False
    for base in related_bases:
        stat = step2_results_raw.get(base, {"loss": 100})
        is_up = stat['loss'] < 100
        if is_up: any_base_up = True
        bts_pop_response.append(
            BTSPopResult(base_ip=base, status="UP" if is_up else "DOWN")
        )

    # DECISION LOGIC STEP 2
    if any_base_up:
        logger.warning(f"Result: FAULT - Isolated Base Sector Failure")
        return DiagnosisResponse(
            parallel_check=parallel_check_response,
            bts_pop_scan=bts_pop_response,
            loopback=None,
            final_status="FAULT – Isolated Base Sector Failure",
            root_cause_level="base"
        )

    # ------------------------------------------------------
    # STEP 3: LOOPBACK CHECK (FINAL AUTHORITY)
    # ------------------------------------------------------
    loopback_ip = target_record.get('loopback_ip')
    if not loopback_ip:
        # Fallback if loopback missing in inventory
        logger.error("Loopback IP missing in inventory.")
        loopback_ip = "127.0.0.1" # Dummy

    logger.info(f"Step 3: Checking Loopback {loopback_ip}")
    step3_stat = await run_single_ping(loopback_ip)
    
    loopback_resp = LoopbackResult(
        ip=loopback_ip,
        status="UP" if step3_stat['loss'] < 100 else "DOWN"
    )

    # DECISION LOGIC STEP 3
    if step3_stat['loss'] < 100:
        logger.critical(f"Result: CRITICAL - Router Alive, Backhaul/Fiber/Power Issue")
        return DiagnosisResponse(
            parallel_check=parallel_check_response,
            bts_pop_scan=bts_pop_response,
            loopback=loopback_resp,
            final_status="CRITICAL – Router Alive, Backhaul / Fiber / Power Issue",
            root_cause_level="loopback"
        )
    else:
        logger.critical(f"Result: CRITICAL - POP/BTS Router DOWN")
        return DiagnosisResponse(
            parallel_check=parallel_check_response,
            bts_pop_scan=bts_pop_response,
            loopback=loopback_resp,
            final_status="CRITICAL – POP / BTS Router DOWN",
            root_cause_level="loopback"
        )

# ---------------------------------------------------------
# UI DATA ENDPOINT (HIERARCHICAL)
# ---------------------------------------------------------

@app.get("/api/inventory")
async def get_inventory_hierarchy():
    """
    Returns data structured for Frontend UI:
    BTS/POP -> List of Clients
    """
    hierarchy = {}
    
    for item in inventory_cache:
        # Key by BTS (or POP if BTS missing)
        key = item.get('bts') if item.get('bts') else item.get('pop')
        if not key: continue
        
        if key not in hierarchy:
            hierarchy[key] = []
            
        hierarchy[key].append({
            "client": item['client'],
            "ip": item['client_ip'],
            "base": item['base_ip']
        })
        
    return hierarchy

@app.get("/api/refresh")
async def refresh_inventory():
    """Endpoint to force reload data from GitHub"""
    await fetch_inventory()
    return {"status": "success", "message": "Inventory reloaded"}
