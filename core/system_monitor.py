"""
E.D.I.T.H. System Telemetry & Monitor
Provides real-time local hardware and OS diagnostics without cloud telemetry.
"""
import time
import platform
import psutil

class SystemMonitor:
    def __init__(self):
        self.start_time = time.time()
        # Initialize initial CPU reading
        psutil.cpu_percent(interval=None)

    def get_telemetry(self) -> dict:
        """Collect current system metrics."""
        try:
            cpu_usage = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            total_ram_gb = round(mem.total / (1024 ** 3), 1)
            used_ram_gb = round(mem.used / (1024 ** 3), 1)
            available_ram_gb = round(mem.available / (1024 ** 3), 1)
            ram_percent = mem.percent

            # Battery status (may be None on desktop computers)
            battery = psutil.sensors_battery()
            if battery:
                battery_percent = round(battery.percent)
                power_plugged = battery.power_plugged
                battery_status = "Charging" if power_plugged else "Discharging"
            else:
                battery_percent = 100
                power_plugged = True
                battery_status = "A/C Line Powered"

            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_free_gb = round(disk.free / (1024 ** 3), 1)

            # Uptime
            uptime_seconds = int(time.time() - self.start_time)
            mins, secs = divmod(uptime_seconds, 60)
            hours, mins = divmod(mins, 60)
            uptime_str = f"{hours:02d}:{mins:02d}:{secs:02d}"

            return {
                "cpu_percent": cpu_usage,
                "ram_percent": ram_percent,
                "ram_used_gb": used_ram_gb,
                "ram_total_gb": total_ram_gb,
                "ram_available_gb": available_ram_gb,
                "battery_percent": battery_percent,
                "battery_plugged": power_plugged,
                "battery_status": battery_status,
                "disk_percent": disk_percent,
                "disk_free_gb": disk_free_gb,
                "uptime": uptime_str,
                "os": f"{platform.system()} {platform.release()}",
                "status": "NOMINAL",
                "security_protocol": "ACTIVE - LOCALHOST ONLY"
            }
        except Exception as e:
            return {
                "cpu_percent": 0.0,
                "ram_percent": 0.0,
                "ram_used_gb": 0.0,
                "ram_total_gb": 16.0,
                "ram_available_gb": 16.0,
                "battery_percent": 100,
                "battery_plugged": True,
                "battery_status": "Standard",
                "disk_percent": 0.0,
                "disk_free_gb": 0.0,
                "uptime": "00:00:00",
                "os": platform.system(),
                "status": f"DIAG_ERR: {str(e)}",
                "security_protocol": "ACTIVE"
            }
