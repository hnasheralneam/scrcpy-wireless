import ipaddress
import subprocess
import threading
import queue
import netifaces
import time
import os

# Define the number of threads to use for parallel scanning.
NUM_THREADS = 50

# The ADB port for wireless connections is typically 5555.
ADB_PORT = 5555

# Use a global event to signal all threads to stop once a connection is made.
# This is a safe way to handle thread termination.
stop_event = threading.Event()

def get_local_network_info():
    """
    Finds the first non-loopback IPv4 address and its subnet mask.
    Returns the network address (e.g., '192.168.1.0/24') or None if not found.
    """
    try:
        # Get a list of all network interfaces
        interfaces = netifaces.interfaces()
        
        for iface in interfaces:
            # Check for IPv4 addresses on the interface
            addresses = netifaces.ifaddresses(iface)
            if netifaces.AF_INET in addresses:
                for link in addresses[netifaces.AF_INET]:
                    ip_address = link['addr']
                    netmask = link.get('netmask')

                    # Skip loopback and other non-usable addresses
                    if ip_address != '127.0.0.1' and netmask:
                        # Use ipaddress module to create a network object from the IP and netmask
                        network = ipaddress.IPv4Network(f"{ip_address}/{netmask}", strict=False)
                        print(f"Discovered local network: {network}")
                        return network
    except Exception as e:
        print(f"Error discovering network info: {e}")
    return None

def ping_host(ip_address):
    """
    Pings an IP address to check if the host is reachable.
    Returns True if the host is reachable, False otherwise.
    """
    # The ping command varies slightly between OSes
    param = '-n 1' if os.name == 'nt' else '-c 1'
    command = ['ping', param, str(ip_address)]
    
    try:
        # Use subprocess to run the ping command. We capture output and don't show it.
        # `timeout` is crucial to avoid hanging on unreachable hosts.
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False

def attempt_adb_connect(ip_address):
    """
    Attempts to connect to a given IP address via ADB.
    Returns True if a connection is established, False otherwise.
    """
    adb_address = f"{ip_address}:{ADB_PORT}"
    print(f"Attempting to connect to {adb_address} via ADB...")
    try:
        # Use adb to connect to the IP address with the specified port.
        command = ["adb", "connect", adb_address]
        
        # Capture and print the output for feedback.
        # Check `adb devices` output to confirm connection.
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=5)
        print(f"ADB connection attempt to {adb_address}:\n{result.stdout}")
        
        # Heuristic check to see if the connection was successful
        if "connected to" in result.stdout:
            print(f"Successfully connected to {ip_address} via ADB!")
            return True
        else:
            return False
            
    except FileNotFoundError:
        print("Error: 'adb' command not found. Please install the Android SDK Platform-Tools.")
    except subprocess.TimeoutExpired:
        print(f"Timeout: ADB connection to {adb_address} timed out.")
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to connect to {adb_address}. Check the device's wireless debugging status.")
        print(e.stderr)
    return False

def worker(queue):
    """
    The worker function for each thread. It gets an IP from the queue,
    pings it, and if it's alive, attempts an ADB connection. It stops if a
    connection has already been established by another thread.
    """
    while not stop_event.is_set():
        try:
            ip_address = queue.get(timeout=1)
            print(f"Worker {threading.current_thread().name} checking {ip_address}...")
            
            if ping_host(ip_address):
                print(f"Host {ip_address} is online.")
                if attempt_adb_connect(ip_address):
                    # Set the stop event to signal other threads to finish
                    stop_event.set()
            
            queue.task_done()
        except queue.Empty:
            # The queue is now empty, so the worker can exit.
            break
        except Exception as e:
            print(f"An unexpected error occurred in worker thread: {e}")

def main():
    """
    Main function to orchestrate the network scan and ADB connections.
    """
    network = get_local_network_info()
    if not network:
        print("Could not determine local network. Exiting.")
        return

    # Create a queue and populate it with all hosts in the network.
    ip_queue = queue.Queue()
    for ip in network.hosts():
        ip_queue.put(ip)

    print(f"Scanning {ip_queue.qsize()} hosts on the network...")
    print("This may take a while. Press Ctrl+C to stop.")

    # Create and start the worker threads
    threads = []
    for _ in range(NUM_THREADS):
        worker_thread = threading.Thread(target=worker, args=(ip_queue,))
        worker_thread.daemon = True
        worker_thread.start()
        threads.append(worker_thread)

    # Wait for all the tasks in the queue to be completed or for the stop event to be set.
    while not stop_event.is_set():
        if ip_queue.empty():
            break
        time.sleep(1)

    # Wait for all the threads to gracefully stop.
    for thread in threads:
        if thread.is_alive():
            thread.join()

    print("\nNetwork scan complete. Script exiting.")

if __name__ == "__main__":
    main()

