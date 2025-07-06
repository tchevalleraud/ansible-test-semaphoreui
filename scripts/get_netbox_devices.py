#!/usr/bin/env python3
import argparse
import requests
import json
import os
import sys

def get_devices(netbox_url, headers):
    r = requests.get(f"{netbox_url}/api/dcim/devices/?limit=1000", headers=headers)
    r.raise_for_status()
    return r.json()["results"]

def get_sites(netbox_url, headers):
    r = requests.get(f"{netbox_url}/api/dcim/sites/?limit=1000", headers=headers)
    r.raise_for_status()
    return r.json()["results"]

def get_regions(netbox_url, headers):
    r = requests.get(f"{netbox_url}/api/dcim/regions/?limit=1000", headers=headers)
    r.raise_for_status()
    return r.json()["results"]

def build_region_dict(regions):
    return {region["id"]: region for region in regions}

def build_site_dict(sites):
    return {site["id"]: site for site in sites}

def build_path_from_site(site, region_dict):
    path = []
    region = site.get("region")
    while region:
        region_obj = region_dict.get(region["id"])
        if not region_obj:
            break
        path.insert(0, region_obj["name"])
        region = region_obj.get("parent")
    path.append(site["name"])
    return path

def get_primary_ip(device):
    primary_ip4 = device.get("primary_ip4")
    primary_ip6 = device.get("primary_ip6")
    if primary_ip4:
        return primary_ip4.get("address").split("/")[0]
    elif primary_ip6:
        return primary_ip6.get("address").split("/")[0]
    return None

def main():
    parser = argparse.ArgumentParser(description="Export NetBox devices with IP and path")
    parser.add_argument("--url", help="Base URL of NetBox", default=os.getenv("NETBOX_URL"))
    parser.add_argument("--token", help="NetBox API token", default=os.getenv("NETBOX_TOKEN"))
    parser.add_argument("--output", help="Output file", default="./data/netbox_devices.json")
    args = parser.parse_args()

    if not args.url or not args.token:
        print("❌ Missing NetBox URL or Token")
        sys.exit(1)

    headers = {
        "Authorization": f"Token {args.token}",
        "Content-Type": "application/json"
    }

    regions = get_regions(args.url, headers)
    sites = get_sites(args.url, headers)
    devices = get_devices(args.url, headers)

    region_dict = build_region_dict(regions)
    site_dict = build_site_dict(sites)

    output = []

    for device in devices:
        site = site_dict.get(device["site"]["id"]) if device.get("site") else None
        if not site:
            continue

        path = build_path_from_site(site, region_dict)
        mgmt_ip = get_primary_ip(device)

        output.append({
            "id": device["id"],
            "name": device["name"],
            "mgmt_ip": mgmt_ip,
            "path": "/World/" + "/".join(path)
        })

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(sorted(output, key=lambda x: x["path"]), f, indent=2)

    print(f"✔️ Exported {len(output)} devices to {args.output}")

if __name__ == "__main__":
    main()
