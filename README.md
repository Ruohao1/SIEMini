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
| **Attacker VM**    | 2    | 2 GB | 20 GB     |
| **SIEM VM**        | 4    | 8 GB | 40–60 GB  |
| **Target VM**    | 2    | 2 GB | 20 GB     |

**Networking:**  

- Use NAT or Bridged networking to have access to internet to setup environments. It could be removed later.
- Add custom virtual network (`/dev/vmnet0`), which will simulate the network between the SIEM VM and the Target VM.

## SIEM VM Configuration

You can run the installation script to configure the SIEM VM. It will install the necessary packages and configure the necessary services.

```bash
./setup.sh --host siem 
```

## Target VM Configuration

You can run the installation script to configure the Target VM. It will install the web server and expose it on port 8080

```bash
./setup.sh --host web
```
