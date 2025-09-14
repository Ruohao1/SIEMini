# SIEMini

# VM Network & Configuration Setup

## Virtual Machine Setup

We will use **2 VM and a container** to simulate an attack and detection environment:

1. **Attacker VM**  
This one is not mandatory as you could use your own computer. We recommend using a [Kali Linux VM](https://www.kali.org/get-kali/#kali-virtual-machines). The purpose of the attacker VM is to launch simulated attacks (e.g., port scans, HTTP exploit attempts).  

2. **SIEM VM**  
This VM will handle the main purposes of the SIEMini project, such as collecting logs, detecting intrusions, and visualizing alerts. We will use the [Ubuntu 22.04.3 LTS VM image](https://releases.ubuntu.com/jammy/) as the base for this VM.

```bash
wget https://releases.ubuntu.com/jammy/ubuntu-22.04.5-live-server-amd64.iso
```

3. **Victim container**  
This container will be the target of the simulated attacks, which will be running on the SIEM VM.

### VM Specifications  

| VM / Container      | vCPU | RAM   | Disk Size |
|--------------------|------|------|-----------|
| **Attacker VM**    | 2    | 2 GB | 20 GB     |
| **SIEM VM**        | 4    | 8 GB | 40–60 GB  |

**Networking:**  

- Use NAT or Bridged networking
- Add custom virtual network (`/dev/vmnet0`), which will be used for communication between the attacker and SIEM VM.

## SIEM VM Configuration

You can run the installation script to configure the SIEM VM. It will install the necessary packages and configure the necessary services.

```bash
./install_siem_requirements.sh
```

