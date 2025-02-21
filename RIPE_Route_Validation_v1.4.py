import json
import urllib.request
from datetime import datetime, timedelta
import time
import pytz

# Configuration
PREFIX_CONFIG = {
    "171.18.48.0/24": "48.0/24",
    "171.18.49.0/24": "49.0/24",
    "171.18.50.0/24": "50.0/24",
    "171.18.51.0/24": "51.0/24",
    "171.18.48.0/23": "48.0/23",
    "171.18.50.0/23": "50.0/23"
}

PREFIXES = list(PREFIX_CONFIG.keys())

VALID_UPSTREAMS = {
    "171.18.48.0/24": ["AS3758"],
    "171.18.49.0/24": ["AS17645"],
    "171.18.50.0/24": ["AS3758"],
    "171.18.51.0/24": ["AS17645"],
    "171.18.48.0/23": ["AS3758", "AS17645"],
    "171.18.50.0/23": ["AS3758", "AS17645"]
}

def get_sgt_time():
    """Convert current UTC time to SGT"""
    utc_time = datetime.now(pytz.UTC)
    sgt = pytz.timezone('Asia/Singapore')
    return utc_time.astimezone(sgt)

def analyze_bgp_data(data, prefix):
    """Analyze BGP data for a single prefix"""
    stats = {
        'total_paths': 0,
        'AS10236': 0,
        'AS19905': 0,
        'OTHER': 0,
        'AS3758': 0,
        'AS17645': 0
    }

    valid_upstreams = VALID_UPSTREAMS[prefix]

    for rrc in data['data']['rrcs']:
        peers = rrc['peers']
        stats['total_paths'] += len(peers)

        for peer in peers:
            # Origin ASN counting
            if peer['asn_origin'] == '10236':
                stats['AS10236'] += 1
            elif peer['asn_origin'] == '19905':
                stats['AS19905'] += 1
            else:
                stats['OTHER'] += 1

            # Upstream ASN counting
            as_path = peer['as_path'].split()
            if len(as_path) >= 2:
                i = len(as_path) - 2
                while i >= 0 and as_path[i] == peer['asn_origin']:
                    i -= 1
                if i >= 0:
                    second_last = as_path[i]
                    if second_last == '3758' and 'AS3758' in valid_upstreams:
                        stats['AS3758'] += 1
                    elif second_last == '17645' and 'AS17645' in valid_upstreams:
                        stats['AS17645'] += 1

    return stats

def fetch_and_analyze_bgp():
    """Fetch and analyze BGP data for all prefixes"""
    sgt_time = get_sgt_time()
    timestamp = sgt_time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n=== Analysis at {timestamp} SGT ===")

    all_stats = {}
    for prefix in PREFIXES:
        url = f"https://stat.ripe.net/data/looking-glass/data.json?resource={prefix}"
        try:
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode('utf-8'))
                stats = analyze_bgp_data(data, prefix)
                all_stats[prefix] = stats

                print(f"\nPrefix: {prefix}")
                print(f"Origin ASNs - AS10236: {stats['AS10236']}, "
                      f"AS19905: {stats['AS19905']}, "
                      f"Others: {stats['OTHER']}")
                print(f"Upstream ASNs - ", end='')
                for asn in VALID_UPSTREAMS[prefix]:
                    print(f"{asn}: {stats[asn]} ", end='')
                print()

        except Exception as e:
            print(f"Error analyzing {prefix}: {e}")
            all_stats[prefix] = None

    return all_stats

def main():
    """Main execution function"""
    print("Starting BGP Route Validation...")
    print("Press Ctrl+C to exit")

    interval_minutes = 2

    while True:
        try:
            fetch_and_analyze_bgp()
            print(f"\nWaiting {interval_minutes} minutes until next check...")
            time.sleep(interval_minutes * 60)

        except KeyboardInterrupt:
            print("\nStopping BGP Analysis...")
            break
        except Exception as e:
            print(f"\nUnexpected error: {e}")
            time.sleep(interval_minutes * 60)

if __name__ == "__main__":
    main()