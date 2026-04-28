"""
gstin_validator.py - GSTIN Validation
"""
import re

GSTIN_PATTERN = re.compile(r'^[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$')

STATE_CODES = {
    "01":"Jammu & Kashmir","02":"Himachal Pradesh","03":"Punjab","04":"Chandigarh",
    "05":"Uttarakhand","06":"Haryana","07":"Delhi","08":"Rajasthan","09":"Uttar Pradesh",
    "10":"Bihar","18":"Assam","19":"West Bengal","20":"Jharkhand","21":"Odisha",
    "22":"Chhattisgarh","23":"Madhya Pradesh","24":"Gujarat","27":"Maharashtra",
    "29":"Karnataka","30":"Goa","32":"Kerala","33":"Tamil Nadu","34":"Puducherry",
    "36":"Telangana","37":"Andhra Pradesh",
}


def validate_gstin_format(gstin):
    if not gstin:
        return {"valid": False, "message": "GSTIN is empty", "state": None}
    gstin = gstin.strip().upper()
    if len(gstin) != 15:
        return {"valid": False, "message": "GSTIN must be 15 characters (got " + str(len(gstin)) + ")", "state": None}
    if not GSTIN_PATTERN.match(gstin):
        return {"valid": False, "message": "Invalid GSTIN format", "state": None}
    state_code = gstin[:2]
    state_name = STATE_CODES.get(state_code, "Unknown State")
    return {
        "valid":      True,
        "gstin":      gstin,
        "state_code": state_code,
        "state":      state_name,
        "pan":        gstin[2:12],
        "message":    "Valid — Registered in " + state_name,
    }


def validate_gstin_list(gstin_list):
    results = []
    seen = {}
    for gstin in gstin_list:
        if gstin in seen:
            results.append({**seen[gstin], "duplicate": True})
        else:
            result = validate_gstin_format(gstin)
            result["duplicate"] = False
            seen[gstin] = result
            results.append(result)
    return results
