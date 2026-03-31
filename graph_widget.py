from collections import deque # Tambahkan di baris paling atas
import time # Tambahkan di bagian import paling atas

class SerialWorker(QObject):
    data_received = pyqtSignal(dict)
    raw_data_received = pyqtSignal(str)
    status_changed = pyqtSignal(bool, str)

    def __init__(self, port, baud, mapping, primary_path=None, redundant_path=None):
        super().__init__()
        self.port = port
        self.baud = baud
        self.mapping = mapping
        self.primary_path = primary_path
        self.redundant_path = redundant_path
        self.running = True
        self.is_logging = False

    def run(self):
        try:
            ser = serial.Serial(self.port, self.baud, timeout=0.1)
            self.status_changed.emit(True, f"Terhubung ke {self.port}")
            
            # Siapkan file jika logging aktif
            f_primary = open(self.primary_path, 'a') if self.primary_path else None
            f_redundant = open(self.redundant_path, 'a') if self.redundant_path else None

            while self.running:
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if not line: continue
                    
                    self.raw_data_received.emit(line)
                    
                    # LOGGING CADANGAN (Simpan data mentah/Raw)
                    if self.is_logging and f_redundant:
                        f_redundant.write(f"{line}\n")
                        f_redundant.flush() # Pastikan data tertulis ke disk

                    # PARSING
                    raw_values = line.split(',')
                    parsed_data = {}
                    for item in self.mapping:
                        idx = item['index']
                        name = item['name']
                        if idx < len(raw_values):
                            parsed_data[name] = raw_values[idx].strip()
                    
                    if parsed_data:
                        self.data_received.emit(parsed_data)
                        
                        # LOGGING UTAMA (Simpan data CSV hasil parse)
                        if self.is_logging and f_primary:
                            csv_line = ",".join([str(v) for v in parsed_data.values()])
                            f_primary.write(f"{csv_line}\n")
                            f_primary.flush()
            
            if f_primary: f_primary.close()
            if f_redundant: f_redundant.close()
            ser.close()
        except Exception as e:
            self.status_changed.emit(False, f"Error: {str(e)}")

    def stop(self):
        self.running = False

class PlaybackWorker(QObject):
    data_received = pyqtSignal(dict)
    status_changed = pyqtSignal(bool, str)
    finished = pyqtSignal()

    def __init__(self, file_path, mapping):
        super().__init__()
        self.file_path = file_path
        self.mapping = mapping
        self.running = True

    def run(self):
        try:
            with open(self.file_path, 'r') as f:
                # Lewati header jika ada
                lines = f.readlines()
                self.status_changed.emit(True, f"Memutar: {self.file_path}")
                
                for line in lines:
                    if not self.running: break
                    
                    # LOGIKA PEMETAAN (Sama dengan Serial)
                    raw_values = line.strip().split(',')
                    parsed_data = {}
                    for item in self.mapping:
                        idx = item['index']
                        name = item['name']
                        if idx < len(raw_values):
                            parsed_data[name] = raw_values[idx].strip()
                    
                    if parsed_data:
                        self.data_received.emit(parsed_data)
                    
                    # Jeda simulasi (misal 50Hz = 0.02s) agar tidak terlalu cepat
                    time.sleep(0.02) 

            self.status_changed.emit(False, "Playback selesai.")
            self.finished.emit()
        except Exception as e:
            self.status_changed.emit(False, f"Error Playback: {e}")