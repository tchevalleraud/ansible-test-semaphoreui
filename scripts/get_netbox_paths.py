#!/usr/bin/env python3
import argparse
import requests
import json
import os
import sys

def get_regions(netbox_url, headers):
    r = requests.get(f"{netbox_url}/api/dcim/regions/?limit=1000", headers=headers)
    r.raise_for_status()
    return r.json()["results"]

def get_sites(netbox_url, headers):
    r = requests.get(f"{netbox_url}/api/dcim/sites/?limit=1000", headers=headers)
    r.raise_for_status()
    return r.json()["results"]

def build_region_dict(regions):
    return {region["id"]: region for region in regions}

def build_path(entry, region_dict):
    path = []
    if "region" in entry and entry["region"]:
        region = region_dict[entry["region"]["id"]]
    elif "parent" in entry:
        region = entry
    else:
        return [entry["name"]]

    while region:
        path.insert(0, region["name"])
        parent = region.get("parent")
        if parent:
            region = region_dict.get(parent["id"])
        else:
            region = None

    if "region" in entry:
        path.append(entry["name"])

    return path

def main():
    parser = argparse.ArgumentParser(description="Generate NetBox region/site paths")
    parser.add_argument("--url", help="Base URL of NetBox", default=os.getenv("NETBOX_URL"))
    parser.add_argument("--token", help="NetBox API token", default=os.getenv("NETBOX_TOKEN"))
    parser.add_argument("--output", help="Output file", default="./data/netbox_paths.json")
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
    region_dict = build_region_dict(regions)

    output = []

    for region in regions:
        path = build_path(region, region_dict)
        output.append({
            "type": "region",
            "slug": region["slug"],
            "name": region["name"],
            "path": "/World/" + "/".join(path)
        })

    for site in sites:
        path = build_path(site, region_dict)
        output.append({
            "type": "site",
            "slug": site["slug"],
            "name": site["name"],
            "path": "/World/" + "/".join(path)
        })

    with open(args.output, "w") as f:
        json.dump(sorted(output, key=lambda x: x["path"]), f, indent=2)

    print(f"✔️ Enriched NetBox paths exported to {args.output}")

if __name__ == "__main__":
    main()