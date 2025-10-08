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

| VM / Container      | vCPU | RAM   | Disk Size | IPv4 |
|--------------------|------|------|-----------| --- |
| **SIEM VM**        | 4    | 8 GB | 40–60 GB  | 192.168.2.100 |
| **Attacker VM**    | 2    | 2 GB | 20 GB     | 192.168.2.150 |
| **Target VM**    | 2    | 2 GB | 20 GB     | 192.168.2.200 |

**Networking:**  

- Use a custom virtual network (`/dev/vmnet0`). We will use static IP addresses to simplify networking configuration.
- Add NAT or Bridged networking to have access to internet to setup environments. It could be removed later.

## VM Configuration

```bash
pip install -r requirements.txt
python main.py setup
```
