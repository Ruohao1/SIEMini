# SIEMini

# VM Network & Configuration Setup

## Virtual Machine Setup

We will use **3 VMs** to simulate an attack and detection environment:

1. **Attacker VM**  
This one is not mandatory as you could use your own computer. We recommend using a [Kali Linux VM](https://www.kali.org/get-kali/#kali-virtual-machines). The purpose of the attacker VM is to launch simulated attacks (e.g., port scans, HTTP exploit attempts).  

2. **SIEM VM**  
This VM will handle the main purposes of the SIEMini project, such as collecting logs, detecting intrusions, and visualizing alerts. We will use the [Ubuntu 22.04.3 LTS VM image](https://releases.ubuntu.com/jammy/) as the base for this VM.

```bash
wget https://releases.ubuntu.com/jammy/ubuntu-22.04.5-live-server-amd64.iso
```

3. **Target VM**  
This VM will be used as the target for the simulated attacks. We will use the [Ubuntu 22.04.3 LTS VM image](https://releases.ubuntu.com/jammy/) as the base for this VM. We will expose a web server on port 80 to receive simulated attacks.

### VM Specifications  

| VM / Container      | vCPU | RAM   | Disk Size |
|--------------------|------|------|-----------|
| **SIEM VM**        | 4    | 8 GB | 40–60 GB  |
| **Attacker VM**    | 2    | 2 GB | 20 GB     |
| **Target VM**    | 2    | 2 GB | 20 GB     |

**Networking:**  

- Use a custom virtual network (`/dev/vmnet0`). We will use static IP addresses to simplify networking configuration.
- Add NAT or Bridged networking to have access to internet to setup environments. It could be removed later.

---

## Quick start

```bash
# 1) Python venv and deps
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2) Bootstrap local helpers (e.g., inventory validation, secrets)
python main.py setup

# 3) Provision the lab
ansible-playbook siemini/main.yml -i siemini/inventory/hosts.ini -v
```

**Assumptions baked into this playbook (per your specs):**

- OS: **Ubuntu 22.04** for all three VMs.
- IDS: **Snort** (community/ET rules configurable).
- Log transport (Web → SIEM): **RFC3164/UDP 514**.
- Kibana: default port **5601**, credentials stored in `/opt/elasticsearch/config/.env` (generated).
- TLS: **enabled** between Logstash ↔ Elasticsearch and Kibana ↔ Elasticsearch.
- Web app: **juicehop** (sample app on **:8080**).

---

## What the Ansible playbook does

Running `ansible-playbook siemini/main.yml -i siemini/inventory/hosts.ini -v` will:

### On the SIEM node (`[siem]`, VM 2 — `<SIEM-IP>`)

1. **Install Elastic Stack (tarballs under `/opt/*`):**
   - Elasticsearch under `/opt/elasticsearch` with a dedicated data dir and JVM heap sizing.
   - Kibana under `/opt/kibana`.
   - Logstash under `/opt/logstash`.
   - Create systemd units: `elasticsearch.service`, `kibana.service`, `logstash.service`.

2. **Secure Elasticsearch + store secrets:**
   - Create `/opt/elasticsearch/config/.env` with generated credentials and enrollment/CA artifacts.
   - Enable TLS for the HTTP layer and transport where needed (self-signed).

3. **Logstash pipelines:**
   - Register `pipelines.yml` entries for:
     - `apache_syslog` — parses Apache access logs forwarded from the Web VM.
     - `snort_alerts` — ingests Snort fast/full alerts.
   - Install pipeline configs in `/opt/logstash/config/pipelines/` including:
     - Apache grok patterns (combined + vhost-friendly), GeoIP enrichment into `source.geo`, user agent parsing, query-length computation, ECS-ish field normalization.
     - Snort parser mapping priority/classification into `event.severity`, `rule.category`, and `related.ip`.
   - Outputs use **HTTPS** and basic auth to Elasticsearch with CA validation (TLS **enabled**).

4. **Index templates + ILM:**
   - Create index templates and rollover ILM policies for:
     - `apache-access-*`
     - `snort-alerts-*`
   - Default retention is conservative (override via `group_vars/siem.yml`).

5. **Kibana setup:**
   - Create data views for the above indices.
   - Import saved objects: searches, lens visualizations, and a compact **“Operations”** dashboard (Apache + Snort).

6. **Snort sensor (local on the SIEM):**
   - Install Snort packages and rule sources (configurable: community or ET Open).
   - Enable a `systemd` unit writing alerts to a Logstash-watched path (fast/full format).
   - Normalize interface and HOME_NET from `group_vars/siem.yml`.

7. **Network exposure (minimal):**
   - Open `5601/tcp` (Kibana) on the SIEM. Elasticsearch `9200/tcp` is local-only by default.
   - Logstash listens on `601/tcp` (kept for future use) and **`514/udp`** for syslog inputs from the Web VM, as specified.

### On the Web node (`[web]`, VM 3 — `<WEB-IP>`, “juicehop”)

1. **Apache + app (port :8080):**
   - Install Apache and a simple **juicehop** app/site bound to `:8080`.
   - Access log format set to combined (with vhost if present). A local troubleshooting copy is kept at `/var/lib/siem/apache.log`.

2. **Syslog shipping to SIEM (RFC3164/UDP 514):**
   - Install and configure **syslog-ng** to forward Apache access logs to `<SIEM-IP>:514/udp`.
   - Ensure hostname preservation and a small disk-backed queue to survive transient SIEM outages.

3. **Optional extras (tag-controlled):**
   - mod_security sample rules (disabled by default).
   - Simple synthetic endpoints to make detections demonstrable (e.g., `/rest/user/login`).

### On the Attacker node (`[attacker]`, VM 1 — `<ATTACKER-IP>`)

1. **Operators’ toolkit:**
   - `curl`, `nmap`, `gobuster`, `nikto`, `hydra`, `wrk`/`ab`, `jq`, etc.
2. **Reproducible scenarios:**
   - Helper scripts in `~/attacks/` to produce brute-force bursts, directory traversal probes, and HTTP fuzz noise against `<WEB-IP>:8080`.

---

## Inventory

Example `siemini/inventory/hosts.ini` with placeholders:

```ini
[siem]
siem ansible_host=<SIEM-IP> ansible_user=siem

[web]
web ansible_host=<WEB-IP> ansible_user=web

[attacker]
attacker ansible_host=<ATTACKER-IP> ansible_user=attacker
```

---

## Key variables (overridable)

`group_vars/siem.yml`:

```yaml
elastic_version: "9.1.5"
es_heap: "1g"
es_host: "https://localhost:9200"  # TLS enabled
es_user: "elastic"
es_env_file: "/opt/elasticsearch/config/.env"  # contains generated password
kibana_host: "http://0.0.0.0:5601"

# Logstash listeners on SIEM
logstash_syslog_udp_port: 514
logstash_syslog_tcp_port: 601   # reserved for RFC5424/TCP if needed later
logstash_apache_pipeline_id: "apache_syslog"
logstash_snort_pipeline_id: "snort_alerts"

# ILM defaults
ilm_hot_max_age: "7d"
ilm_delete_after: "30d"

# Snort
snort_iface: "ens33"          # set per your VM
snort_home_net: "<WEB-IP>/32" # typical single host target
snort_rule_source: "community" # or "et-open"
```

`group_vars/web.yml`:

```yaml
apache_listen_port: 8080
syslog_dest_host: "<SIEM-IP>"
syslog_dest_port_udp: 514
app_name: "juicehop"
```

---

## Running with tags

```bash
# Only SIEM node (Elastic, Logstash, Kibana, Snort, pipelines)
ansible-playbook siemini/main.yml -i siemini/inventory/hosts.ini -v -t siem

# Only Web + syslog shipping
ansible-playbook siemini/main.yml -i siemini/inventory/hosts.ini -v -t web

# Only Attacker tooling
ansible-playbook siemini/main.yml -i siemini/inventory/hosts.ini -v -t attacker
```

---

## Verification checklist

### 1) Web app reachable on :8080

```bash
curl -si http://<WEB-IP>:8080/ | sed -n '1,10p'
```

### 2) Syslog flow (Web → SIEM via UDP 514)

On the SIEM, confirm Logstash is listening and receiving:

```bash
sudo ss -lunp | grep 514
sudo journalctl -u logstash -e | tail -n 50
curl -s http://localhost:9600/_node/stats/pipelines?pretty | jq '.pipelines'
```

### 3) Documents in Elasticsearch

```bash
# Source ES password from the generated env file
set -a; . /opt/elasticsearch/config/.env; set +a

# Apache docs count
curl -k -u "$ES_USERNAME:$ES_PASSWORD" \
  "https://localhost:9200/apache-access-*/_count?pretty"

# Snort alerts (any)
curl -k -u "$ES_USERNAME:$ES_PASSWORD" \
  "https://localhost:9200/snort-alerts-*/_search?q=event.severity:*&size=1&pretty"
```

### 4) Kibana access

Open: `http://<SIEM-IP>:5601`  
Use the credentials from `/opt/elasticsearch/config/.env`.  
Verify data views `apache-access-*` and `snort-alerts-*` exist, and load the **Operations** dashboard.

---

## Built‑in demo scenarios

> Run these from the **Attacker** VM against the **Web** VM (`<WEB-IP>:8080`). They create visible signals in Kibana.

**A) Brute-force spray (401 flood)**

```bash
for i in $(seq 1 20); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST "http://<WEB-IP>:8080/rest/user/login" \
    -d "u=alice&p=$RANDOM"
done
```

**Signal:** spike in `http.response.status_code: 401`, aggregation by `source.ip`, and repeated `user.name` values.

**B) Directory traversal probes**

```bash
for p in /../../etc/passwd /..%2f..%2f/etc/passwd; do
  curl -s "http://<WEB-IP>:8080/$p" -A "scanner" -o /dev/null
done
```

**Signal:** `url.path` contains traversal metacharacters, `user_agent.original: scanner`.

**C) SQLi smoke**

```bash
curl -s "http://<WEB-IP>:8080/search?q=' OR 1=1 -- -" -o /dev/null
```

**Signal:** suspicious query tokens in `url.query`, flagged by pipeline tagging and dashboards.

**D) Recon to trigger Snort**

```bash
sudo nmap -sX -Pn <WEB-IP> -p 8080
sudo nmap -sN -Pn <WEB-IP> -p 8080
```

**Signal:** Snort rules fire, mapped into `event.severity`, `rule.category`, and `related.ip` fields.

---

## File/Path layout (created by playbook)

- `/opt/elasticsearch`, `/opt/kibana`, `/opt/logstash`
- `/etc/systemd/system/{elasticsearch,kibana,logstash}.service`
- `/opt/logstash/config/pipelines.yml`
- `/opt/logstash/config/pipelines/apache_access.conf`
- `/opt/logstash/config/pipelines/snort_alerts.conf`
- `/etc/syslog-ng/syslog-ng.conf` and `/etc/syslog-ng/conf.d/10-web-to-siem.conf` (Web VM)
- `/var/lib/siem/apache.log` (local troubleshooting copy on Web VM)
- Kibana saved objects (data views, dashboard)

---

## Troubleshooting

- **No logs in ES:** Check Logstash node stats and inputs:

  ```bash
  curl -s http://localhost:9600/_node/stats/pipelines?pretty | jq '.pipelines'
  sudo journalctl -u logstash -e | sed -n '1,120p'
  ```

  Ensure UDP `514` reaches `<SIEM-IP>`; on Web VM confirm syslog-ng is sending and no queue backlog.

- **Parsing errors (Logstash):** The service log will show the pipeline + byte offset. Fix the referenced grok/field name and restart:

  ```bash
  sudo journalctl -u logstash -e
  sudo systemctl restart logstash
  ```

- **Kibana is empty:** Verify time range and data views (`apache-access-*`, `snort-alerts-*`).

- **TLS issues (LS→ES):** Ensure the CA path used by Logstash matches the Elasticsearch CA bundle and that output uses `ssl_certificate_authorities` with `ssl => true`.
