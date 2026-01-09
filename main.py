import os
import re
import ipaddress
import logging
import tempfile
import asyncio
import csv
import shutil
from typing import List, Optional, Dict, Any
from datetime import datetime

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------
# CONFIGURATION & LOGGING
# ---------------------------------------------------------
FRONTEND_URL = "https://fkoff002-glitch.github.io"
DATA_SOURCE_URL = "https://fkoff002-glitch.github.io/RF-DATA/RF%20Data%20-%20RADIO_LINKS.csv"
LOCAL_FILE_PATH = "inventory.csv"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - NOC-AUTOMATION - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="NOC RF Automation Backend")

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
    level: str
    ip: str
    status: str
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
# INVENTORY MANAGEMENT
# ---------------------------------------------------------
inventory_cache = []
inventory_index = {}

def validate_ip(ip: str) -> bool:
    if not ip or ip == "N/A": return False
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

async def fetch_inventory():
    global inventory_cache, inventory_index
    logger.info("Loading inventory...")
    
    try:
        # Local file priority for reliability
        if os.path.exists(LOCAL_FILE_PATH):
            with open(LOCAL_FILE_PATH, "r", encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                _parse_inventory(reader)
                logger.info(f"Loaded from local: {len(inventory_cache)} records")
        else:
            # Fallback to GitHub
            async with httpx.AsyncClient() as client:
                resp = await client.get(DATA_SOURCE_URL)
                resp.raise_for_status()
                lines = resp.text.splitlines()
                reader = csv.DictReader(lines)
                _parse_inventory(reader)
                logger.info(f"Loaded from GitHub: {len(inventory_cache)} records")

    except Exception as e:
        logger.error(f"Failed to load inventory: {e}")

def _parse_inventory(reader):
    global inventory_cache, inventory_index
    inventory_cache = []
    inventory_index = {"client": {}, "bts": {}, "pop": {}, "ip": {}}
    
    for row in reader:
        client_name = row.get('Client_Name', '').strip()
        bts_name = row.get('BTS_Name', '').strip()
        pop_name = row.get('POP_Name', '').strip()
        base_ip = row.get('Base_IP', '').strip()
        client_ip = row.get('Client_IP', '').strip()
        loopback_raw = row.get('Loopback_IP', '').strip()
        
        loopback_ip = loopback_raw if loopback_raw and loopback_raw.upper() != "N/A" else None

        if not validate_ip(client_ip) or not validate_ip(base_ip):
            continue
        
        record = {
            "client": client_name,
            "bts": bts_name if bts_name else pop_name, 
            "pop": pop_name,
            "client_ip": client_ip,
            "base_ip": base_ip,
            "loopback_ip": loopback_ip
        }
        
        inventory_cache.append(record)
        inventory_index["client"][client_name.lower()] = record
        inventory_index["bts"][record["bts"].lower()] = record 
        inventory_index["pop"][pop_name.lower()] = record
        inventory_index["ip"][client_ip] = record
        inventory_index["ip"][base_ip] = record

@app.on_event("startup")
async def startup_event():
    # Validate Dependencies
    if not shutil.which("fping"):
        logger.critical("FATAL: 'fping' not found. Please run 'sudo apt install fping'.")
        # We do not exit to allow UI to show errors if any, but logging is critical.
    else:
        logger.info("fping detected successfully.")
        
    await fetch_inventory()

# ---------------------------------------------------------
# NETWORK LOGIC
# ---------------------------------------------------------
def calculate_gateway(base_ip: str) -> str:
    try:
        ip_obj = ipaddress.ip_address(base_ip)
        gateway = ipaddress.ip_address(int(ip_obj) - 1)
        return str(gateway)
    except Exception:
        return "0.0.0.0"

def parse_fping_output(output: str) -> Dict[str, dict]:
    results = {}
    # Handle standard fping stats
    pattern_stats = re.compile(
        r'(?P<ip>\d+\.\d+\.\d+\.\d+)\s*:\s*'
        r'(?P<sent>\d+)\s*transmitted,\s*'
        r'(?P<received>\d+)\s*received,\s*'
        r'(?P<loss>\d+)%\s*loss.*'
        r'min/avg/max\s*=\s*[\d.]+/(?P<avg>[\d.]+)/[\d.]+'
    )
    # Handle unreachable hosts
    pattern_unreachable = re.compile(r'(?P<ip>\d+\.\d+\.\d+\.\d+)\s+is\s+unreachable')
    
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
            # Host unreachable = 100% loss
            results[match.group('ip')] = {
                "sent": 0, "received": 0, "loss": 100, "avg": None
            }
            
    return results

async def run_fping_batch(targets: List[str]) -> Dict[str, dict]:
    valid_targets = [t for t in targets if validate_ip(t)]
    if not valid_targets: return {}

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        temp_filename = f.name
        f.write("\n".join(valid_targets))

    try:
        # -l: loop stats, -c 3: 3 packets
        process = await asyncio.create_subprocess_exec(
            'fping', '-l', '-c', '3', '-f', temp_filename,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return parse_fping_output(stdout.decode('utf-8'))
    finally:
        if os.path.exists(temp_filename): os.remove(temp_filename)

async def run_single_ping(ip: str) -> dict:
    res = await run_fping_batch([ip])
    return res.get(ip, {"sent": 0, "received": 0, "loss": 100, "avg": None})

# ---------------------------------------------------------
# DIAGNOSIS ENDPOINT
# ---------------------------------------------------------
rate_limit_store = {}

@app.post("/api/diagnose", response_model=DiagnosisResponse)
async def diagnose_link(search_query: str = Query(...)):
    now = datetime.now().timestamp()
    if search_query in rate_limit_store:
        if now - rate_limit_store[search_query] < 2:
            raise HTTPException(status_code=429, detail="Too many requests.")
    rate_limit_store[search_query] = now

    query = search_query.lower().strip()
    target_record = None
    
    # Search index
    if query in inventory_index["client"]: target_record = inventory_index["client"][query]
    elif query in inventory_index["ip"]: target_record = inventory_index["ip"][query]
    elif query in inventory_index["bts"]: target_record = inventory_index["bts"][query]
    elif query in inventory_index["pop"]: target_record = inventory_index["pop"][query]
    
    if not target_record:
        raise HTTPException(status_code=404, detail="Target not found.")

    # STEP 1: PARALLEL CHECK
    gateway_ip = calculate_gateway(target_record['base_ip'])
    targets_step1 = [target_record['client_ip'], target_record['base_ip'], gateway_ip]
    step1_results_raw = await run_fping_batch(targets_step1)
    
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

    if client_stat['loss'] < 100:
        return DiagnosisResponse(parallel_check=parallel_check_response, bts_pop_scan=[], loopback=None, final_status="LINK UP – Client Reachable", root_cause_level="client")

    if client_stat['loss'] == 100 and base_stat['loss'] < 100:
        return DiagnosisResponse(parallel_check=parallel_check_response, bts_pop_scan=[], loopback=None, final_status="FAULT – Client Radio / CPE Down", root_cause_level="client")

    # STEP 2: BTS / POP MASS CHECK
    site_bts = target_record.get('bts')
    site_pop = target_record.get('pop')
    related_bases = [item['base_ip'] for item in inventory_cache if item.get('bts') == site_bts or item.get('pop') == site_pop]
    related_bases = list(set(related_bases))
    
    step2_results_raw = await run_fping_batch(related_bases)
    bts_pop_response = []
    any_base_up = False
    
    for base in related_bases:
        stat = step2_results_raw.get(base, {"loss": 100})
        is_up = stat['loss'] < 100
        if is_up: any_base_up = True
        bts_pop_response.append(BTSPopResult(base_ip=base, status="UP" if is_up else "DOWN"))

    if any_base_up:
        return DiagnosisResponse(parallel_check=parallel_check_response, bts_pop_scan=bts_pop_response, loopback=None, final_status="FAULT – Isolated Base Sector Failure", root_cause_level="base")

    # STEP 3: LOOPBACK CHECK
    loopback_ip = target_record.get('loopback_ip')
    if not loopback_ip or not validate_ip(loopback_ip):
        return DiagnosisResponse(parallel_check=parallel_check_response, bts_pop_scan=bts_pop_response, loopback=None, final_status="ERROR – Loopback IP Missing", root_cause_level="unknown")

    step3_stat = await run_single_ping(loopback_ip)
    loopback_resp = LoopbackResult(ip=loopback_ip, status="UP" if step3_stat['loss'] < 100 else "DOWN")

    if step3_stat['loss'] < 100:
        return DiagnosisResponse(parallel_check=parallel_check_response, bts_pop_scan=bts_pop_response, loopback=loopback_resp, final_status="CRITICAL – Router Alive, Backhaul / Fiber / Power Issue", root_cause_level="loopback")
    else:
        return DiagnosisResponse(parallel_check=parallel_check_response, bts_pop_scan=bts_pop_response, loopback=loopback_resp, final_status="CRITICAL – POP / BTS Router DOWN", root_cause_level="loopback")

# ---------------------------------------------------------
# ENDPOINTS
# ---------------------------------------------------------
@app.get("/api/inventory")
async def get_inventory_hierarchy():
    hierarchy = {}
    for item in inventory_cache:
        key = item.get('bts') if item.get('bts') else item.get('pop')
        if not key: continue
        if key not in hierarchy: hierarchy[key] = []
        hierarchy[key].append({"client": item['client'], "ip": item['client_ip'], "base": item['base_ip']})
    return hierarchy

@app.get("/api/refresh")
async def refresh_inventory():
    await fetch_inventory()
    return {"status": "success", "message": "Inventory reloaded"}
