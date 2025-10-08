from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
ANSIBLE_DIR = ROOT_DIR / "siemini"
INVENTORY_DIR = ANSIBLE_DIR / "inventory"
META_FILE = INVENTORY_DIR / ".meta.json"
HOSTS_INI = INVENTORY_DIR / "hosts.ini"
HOST_VARS_DIR = INVENTORY_DIR / "host_vars"

DEFAULTS = {
    "siem": {
        "ansible_user": "ubuntu",
        "syslog_ng_port": 514,
        "elasticsearch_port": 9200,
        "kibana_port": 5601,
        "ids_tool": "snort",
    },
    "target": {"ansible_user": "ubuntu", "web_port": 8080, "ssh_port": 22},
    "attacker": {"ansible_user": "kali", "tools": ["nmap", "curl", "hydra"]},
}
