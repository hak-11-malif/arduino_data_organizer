import sys
import time
import serial
import serial.tools.list_ports
import pyqtgraph as pg
from collections import deque
from PyQt6.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QScrollArea, QGridLayout, QLabel, QFileDialog,
                             QLineEdit, QFrame, QTextEdit, QComboBox, QSplitter, QInputDialog, 
                             QMessageBox, QDialog, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
import json

# --- WORKER: SERIAL CONNECTION ---
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
            
            while self.running:
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if not line: continue
                    
                    self.raw_data_received.emit(line)
                    
                    # Redundant Logging (Raw Data)
                    if self.is_logging and self.redundant_path:
                        with open(self.redundant_path, 'a') as f:
                            f.write(f"{line}\n")

                    # Parsing Logic
                    raw_values = line.split(',')
                    parsed_data = {}
                    for item in self.mapping:
                        idx = item['index']
                        name = item['name']
                        if idx < len(raw_values):
                            parsed_data[name] = raw_values[idx].strip()
                    
                    if parsed_data:
                        self.data_received.emit(parsed_data)
                        
                        # Primary Logging (Parsed Data)
                        if self.is_logging and self.primary_path:
                            with open(self.primary_path, 'a') as f:
                                csv_line = ",".join([str(v) for v in parsed_data.values()])
                                f.write(f"{csv_line}\n")
            ser.close()
        except Exception as e:
            self.status_changed.emit(False, f"Serial Error: {str(e)}")

    def stop(self):
        self.running = False

# --- WORKER: PLAYBACK ---
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
                lines = f.readlines()
                self.status_changed.emit(True, "Memulai Playback...")
                for line in lines:
                    if not self.running: break
                    raw_values = line.strip().split(',')
                    parsed_data = {}
                    for item in self.mapping:
                        idx = item['index']
                        name = item['name']
                        if idx < len(raw_values):
                            parsed_data[name] = raw_values[idx].strip()
                    
                    if parsed_data:
                        self.data_received.emit(parsed_data)
                    time.sleep(0.05) # Kecepatan Playback
            self.finished.emit()
        except Exception as e:
            self.status_changed.emit(False, f"Playback Error: {e}")

# --- WIDGET: GRAPH MODULE ---
class GraphWidget(QFrame):
    def __init__(self, title="Sensor Data", max_points=100):
        super().__init__()
        # 1. Styling & Inisialisasi Dasar
        self.setStyleSheet("background-color: #2b2b2b; border: 1px solid #444; border-radius: 2px;")
        self.sensor_name = title
        self.formula = "x"
        self.max_points = max_points
        self.current_time = 0
        self.data_x = deque(maxlen=max_points)
        self.data_y = deque(maxlen=max_points)

        # 2. Layout Utama
        layout = QVBoxLayout(self)

        # 3. Header: Nama Sensor & Live Value
        header = QHBoxLayout()
        self.label = QLabel(title)
        self.label.setStyleSheet("color: #00ff00; font-weight: bold; border: none;")
        self.val_display = QLabel("0.00")
        self.val_display.setStyleSheet("color: white; font-weight: bold; border: none;")
        header.addWidget(self.label)
        header.addStretch()
        header.addWidget(self.val_display)
        layout.addLayout(header)

        # 4. Plot Area (PyQtGraph)
        self.plot = pg.PlotWidget()
        self.plot.setBackground('#1a1a1a')
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.curve = self.plot.plot(pen=pg.mkPen(color='#00ff00', width=2))
        layout.addWidget(self.plot)

        # 5. Tombol Kontrol (Satu Baris Saja)
        btn_layout = QHBoxLayout()
        self.btn_math = QPushButton("Math Engine")
        self.btn_sumbu = QPushButton("Sumbu")
        self.btn_hapus = QPushButton("Hapus")
        self.btn_export = QPushButton("Export")

        # Styling & Penambahan ke Layout
        for btn in [self.btn_math, self.btn_sumbu, self.btn_hapus, self.btn_export]:
            btn.setStyleSheet("background-color: #444; color: #ddd; font-size: 10px; padding: 2px;")
            btn_layout.addWidget(btn)

        # 6. Menghubungkan Signal ke Slot (Fungsi)
        self.btn_math.clicked.connect(self.open_math_dialog)
        self.btn_sumbu.clicked.connect(self.config_axis)
        self.btn_hapus.clicked.connect(self.remove_self)
        self.btn_export.clicked.connect(self.export_csv)

        layout.addLayout(btn_layout)

    # --- FUNGSI KONTROL ---

    def config_axis(self):
        """Mengatur rentang Y-Axis (Manual atau Auto)"""
        y_min, ok1 = QInputDialog.getDouble(self, "Sumbu Y", f"Batas Bawah {self.sensor_name}:", 0, -10000, 10000, 2)
        if not ok1: return
        y_max, ok2 = QInputDialog.getDouble(self, "Sumbu Y", f"Batas Atas {self.sensor_name}:", 100, -10000, 10000, 2)
        
        if ok2:
            if y_min == 0 and y_max == 0:
                self.plot.enableAutoRange(axis='y')
                QMessageBox.information(self, "Sumbu", "Mode Auto-Scale Aktif")
            else:
                self.plot.setYRange(y_min, y_max, padding=0)

    def remove_self(self):
        """Menghapus modul grafik ini"""
        reply = QMessageBox.question(self, 'Hapus Grafik', f"Hapus grafik {self.sensor_name}?", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.deleteLater()

    def export_csv(self):
        """Export data yang ada di grafik ke file CSV"""
        if not self.data_y:
            QMessageBox.warning(self, "Export", "Data kosong!")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Data", f"{self.sensor_name}.csv", "CSV Files (*.csv)")
        if path:
            try:
                with open(path, 'w') as f:
                    f.write("Time,Value\n")
                    for x, y in zip(self.data_x, self.data_y):
                        f.write(f"{x},{y}\n")
                QMessageBox.information(self, "Export", "Berhasil diekspor!")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Gagal: {e}")

    def open_math_dialog(self):
        """Membuka dialog rumus Math Engine"""
        new_formula, ok = QInputDialog.getText(self, 'Math Engine', 
                                              f'Rumus untuk {self.sensor_name} (gunakan x):', 
                                              text=self.formula)
        if ok: self.formula = new_formula

    def update_value(self, value):
        """Memproses data masuk melalui Math Engine dan mengupdate grafik"""
        try:
            raw_val = float(value)
            # Menghitung dengan rumus Math Engine
            calibrated_val = eval(self.formula.replace('x', str(raw_val)))
            
            self.current_time += 1
            self.data_x.append(self.current_time)
            self.data_y.append(calibrated_val)
            
            # Update kurva & display angka
            self.curve.setData(list(self.data_x), list(self.data_y))
            self.val_display.setText(f"{calibrated_val:.2f}")
        except:
            self.val_display.setText(str(value))
# --- MAIN WINDOW ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AERO-32 Data Organizer")
        self.resize(1280, 800)
        self.setStyleSheet("background-color: #1a1a1a; color: #dcdcdc;")

        self.data_mapping = []
        self.sensor_labels = {}
        self.status_labels = {}
        self.serial_thread = None
        self.worker = None
        self.logging_active = False

        # UI Layout
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self.main_splitter)
        
        self.setup_sidebar()
        
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        self.setup_top_bar(right_layout)
        
        self.content_splitter = QSplitter(Qt.Orientation.Vertical)
        self.setup_graph_area()
        self.setup_command_panel()
        
        self.content_splitter.addWidget(self.graph_area_widget)
        self.content_splitter.addWidget(self.command_panel_widget)
        right_layout.addWidget(self.content_splitter)
        self.main_splitter.addWidget(right_container)

        self.main_splitter.setSizes([300, 980])
        self.init_ui()

    def setup_top_bar(self, layout):
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Profile:"))
        self.profile_select = QComboBox()
        self.profile_select.addItems(["Default_Rocket", "Static_Test"])
        top_bar.addWidget(self.profile_select)
        
        # Beri variabel self.btn_save_config dan self.btn_load_config
        self.btn_save_config = self.style_btn("Save Config", "#333")
        self.btn_load_config = self.style_btn("Load Config", "#333")
        
        top_bar.addWidget(self.btn_save_config)
        top_bar.addWidget(self.btn_load_config)
        top_bar.addStretch()
        
        self.btn_playback = self.style_btn("MODE: PLAYBACK", "#2980b9")
        top_bar.addWidget(self.btn_playback)
        layout.addLayout(top_bar)

    def setup_sidebar(self):
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        container = QWidget(); layout = QVBoxLayout(container)

        # 1. KONEKSI SERIAL
        layout.addWidget(QLabel("SERIAL CONNECTION"))
        conn_box = QFrame(); conn_box.setStyleSheet("background-color: #222; border: 1px solid #444;")
        v_conn = QVBoxLayout(conn_box)
        h_port = QHBoxLayout()
        self.port_combo = QComboBox()
        self.btn_refresh = QPushButton("Ref"); self.btn_refresh.setFixedWidth(40)
        self.btn_refresh.clicked.connect(self.update_ports)
        h_port.addWidget(QLabel("Port:")); h_port.addWidget(self.port_combo); h_port.addWidget(self.btn_refresh)
        v_conn.addLayout(h_port)
        
        h_baud = QHBoxLayout()
        self.baud_combo = QComboBox(); self.baud_combo.addItems(["9600", "115200", "921600"])
        h_baud.addWidget(QLabel("Baud:")); h_baud.addWidget(self.baud_combo)
        v_conn.addLayout(h_baud)
        
        self.btn_connect = self.style_btn("HUBUNGKAN MIKROKONTROLER", "#333")
        v_conn.addWidget(self.btn_connect)
        layout.addWidget(conn_box)

        # 2. LOGGING
        layout.addWidget(QLabel("DATA LOGGING"))
        log_box = QFrame(); log_box.setStyleSheet("background-color: #222; border: 1px solid #444;")
        v_log = QVBoxLayout(log_box)
        self.primary_path = QLineEdit(); self.redundant_path = QLineEdit()
        v_log.addWidget(QLabel("Primary (CSV):"))
        h1 = QHBoxLayout(); h1.addWidget(self.primary_path); btnp1 = QPushButton("Pilih")
        btnp1.clicked.connect(lambda: self.browse_file_path(self.primary_path)); h1.addWidget(btnp1); v_log.addLayout(h1)
        v_log.addWidget(QLabel("Redundant (Raw):"))
        h2 = QHBoxLayout(); h2.addWidget(self.redundant_path); btnp2 = QPushButton("Pilih")
        btnp2.clicked.connect(lambda: self.browse_file_path(self.redundant_path)); h2.addWidget(btnp2); v_log.addLayout(h2)
        self.btn_logging = self.style_btn("START LOGGING", "#333")
        v_log.addWidget(self.btn_logging)
        layout.addWidget(log_box)

        # 3. DASHBOARDS
        layout.addWidget(QLabel("DATA DASHBOARD"))
        self.btn_config_data = self.style_btn("Konfigurasi Data Masuk", "#444")
        layout.addWidget(self.btn_config_data)
        self.dash_container = QFrame(); self.dash_layout = QVBoxLayout(self.dash_container)
        layout.addWidget(self.dash_container)
        
        layout.addWidget(QLabel("ALERT DASHBOARD"))
        self.alert_container = QFrame(); self.alert_layout = QVBoxLayout(self.alert_container)
        layout.addWidget(self.alert_container)

        self.serial_mon = QTextEdit(); self.serial_mon.setReadOnly(True); self.serial_mon.setFixedHeight(120)
        self.serial_mon.setStyleSheet("background-color: #000; color: #0f0; font-family: Consolas; font-size: 10px;")
        layout.addWidget(QLabel("SERIAL MONITOR"))
        layout.addWidget(self.serial_mon)

        layout.addStretch(); scroll.setWidget(container)
        self.main_splitter.addWidget(scroll)

    def init_ui(self):
        self.btn_config_data.clicked.connect(self.open_data_config)
        self.btn_connect.clicked.connect(self.toggle_connection)
        self.btn_logging.clicked.connect(self.toggle_logging)
        self.btn_playback.clicked.connect(self.start_playback_mode)
        self.btn_add_graph.clicked.connect(self.add_new_graph_dialog)
        self.update_ports()
        self.btn_save_config.clicked.connect(self.save_current_config)
        self.btn_load_config.clicked.connect(self.load_config_from_file)

    def toggle_connection(self):
        if self.serial_thread and self.serial_thread.isRunning():
            self.worker.stop(); self.serial_thread.quit(); self.serial_thread.wait()
            self.btn_connect.setText("HUBUNGKAN MIKROKONTROLER"); self.btn_connect.setStyleSheet("background-color: #333;")
        else:
            self.serial_thread = QThread()
            self.worker = SerialWorker(self.port_combo.currentText(), self.baud_combo.currentText(), self.data_mapping)
            self.worker.moveToThread(self.serial_thread)
            self.serial_thread.started.connect(self.worker.run)
            self.worker.data_received.connect(self.process_incoming_data)
            self.worker.raw_data_received.connect(lambda x: self.serial_mon.append(x))
            self.serial_thread.start()
            self.btn_connect.setText("PUTUSKAN KONEKSI"); self.btn_connect.setStyleSheet("background-color: #800;")

    def toggle_logging(self):
        if not self.worker: return
        self.logging_active = not self.logging_active
        self.worker.is_logging = self.logging_active
        self.worker.primary_path = self.primary_path.text()
        self.worker.redundant_path = self.redundant_path.text()
        self.btn_logging.setText("STOP LOGGING" if self.logging_active else "START LOGGING")
        self.btn_logging.setStyleSheet("background-color: #d35400;" if self.logging_active else "background-color: #333;")

    def process_incoming_data(self, data_dict):
        """Routing data dan Konversi Status 0/1"""
        for name, value in data_dict.items():
            
            # --- LOGIKA UNTUK DATA DASHBOARD (SIDEBAR) ---
            if name in self.sensor_labels:
                self.sensor_labels[name].setText(f"{name} : {value}")
            
            # --- LOGIKA UNTUK ALERT DASHBOARD (STATUS) ---
            if name in self.status_labels:
                # Cek jika data adalah 0 atau 1 untuk diubah ke teks manusia
                display_text = value
                color = "#ffaa00" # Warna default (Oranye)

                if value == "0":
                    display_text = "OFF / FALSE / SAFE"
                    color = "#00ff00" # Hijau (Aman)
                elif value == "1":
                    display_text = "ON / TRUE / ARMED"
                    color = "#ff0000" # Merah (Bahaya/Aktif)
                
                self.status_labels[name].setText(f"[{name}] : {display_text}")
                self.status_labels[name].setStyleSheet(f"color: {color}; border:none;")

            # --- LOGIKA UNTUK GRAFIK ---
            for i in range(self.graph_layout.count()):
                item = self.graph_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if isinstance(widget, GraphWidget):
                        if name.lower() in widget.sensor_name.lower():
                            widget.update_value(value)

    def setup_graph_area(self):
        self.graph_area_widget = QWidget(); v = QVBoxLayout(self.graph_area_widget)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        self.graph_container = QWidget(); self.graph_layout = QGridLayout(self.graph_container)
        self.graph_layout.addWidget(GraphWidget("Altitude (m)"), 0, 0)
        scroll.setWidget(self.graph_container); v.addWidget(scroll)
        self.btn_add_graph = QPushButton("+ Tambah Modul Grafik")
        self.btn_add_graph.setStyleSheet("border: 1px dashed #0f0; color: #0f0; padding: 8px;")
        v.addWidget(self.btn_add_graph)

    def setup_command_panel(self):
        self.command_panel_widget = QWidget(); layout = QVBoxLayout(self.command_panel_widget)
        header = QHBoxLayout(); header.addWidget(QLabel("<b>FLIGHT COMMANDS</b>"))
        btn_add = QPushButton("+"); btn_add.setFixedSize(25, 25); btn_add.clicked.connect(self.add_custom_command)
        btn_rem = QPushButton("-"); btn_rem.setFixedSize(25, 25); btn_rem.clicked.connect(self.remove_custom_command)
        header.addStretch(); header.addWidget(btn_add); header.addWidget(btn_rem); layout.addLayout(header)
        self.cmd_buttons_container = QWidget(); self.cmd_buttons_layout = QHBoxLayout(self.cmd_buttons_container)
        self.add_command_button("ARM_IGNITE", "#800"); layout.addWidget(self.cmd_buttons_container)

    def update_ports(self):
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for p in ports: self.port_combo.addItem(p.device)

    def style_btn(self, text, color):
        btn = QPushButton(text); btn.setStyleSheet(f"background-color: {color}; color: white; padding: 5px;")
        return btn

    def browse_file_path(self, edit):
        path, _ = QFileDialog.getSaveFileName(self, "Simpan Ke", "", "CSV (*.csv);;All (*)")
        if path: edit.setText(path)

    def add_custom_command(self):
        name, ok = QInputDialog.getText(self, "Tambah", "Nama Perintah:")
        if ok and name: self.add_command_button(name.upper(), "#333")

    def remove_custom_command(self):
        if self.cmd_buttons_layout.count() > 1:
            w = self.cmd_buttons_layout.takeAt(self.cmd_buttons_layout.count()-1).widget()
            if w: w.deleteLater()

    def add_command_button(self, name, color):
        btn = QPushButton(name); btn.setStyleSheet(f"background-color: {color}; color: white; font-weight: bold; padding: 10px;")
        self.cmd_buttons_layout.addWidget(btn)

    def add_new_graph_dialog(self):
        name, ok = QInputDialog.getText(self, "Tambah Grafik", "Nama Sensor:")
        if ok and name:
            idx = self.graph_layout.count()
            self.graph_layout.addWidget(GraphWidget(name), idx // 2, idx % 2)

    def open_data_config(self):
        dialog = DataConfigDialog(self, self.data_mapping)
        if dialog.exec():
            self.data_mapping = dialog.get_config()
            self.update_dashboard_ui()

    def update_dashboard_ui(self):
        while self.dash_layout.count():
            w = self.dash_layout.takeAt(0).widget()
            if w: w.deleteLater()
        while self.alert_layout.count():
            w = self.alert_layout.takeAt(0).widget()
            if w: w.deleteLater()
        self.sensor_labels.clear(); self.status_labels.clear()
        for item in self.data_mapping:
            lbl = QLabel(f"{item['name']} : 0.00")
            lbl.setStyleSheet("color: #0f0; font-family: Consolas; border: none;")
            if item['type'] == "Data":
                self.dash_layout.addWidget(lbl); self.sensor_labels[item['name']] = lbl
            else:
                lbl.setStyleSheet("color: #fa0; border: none;")
                self.alert_layout.addWidget(lbl); self.status_labels[item['name']] = lbl
        self.dash_layout.addStretch(); self.alert_layout.addStretch()

    def start_playback_mode(self):
        path, _ = QFileDialog.getOpenFileName(self, "Buka Log", "", "CSV (*.csv)")
        if path:
            self.playback_thread = QThread()
            self.playback_worker = PlaybackWorker(path, self.data_mapping)
            self.playback_worker.moveToThread(self.playback_thread)
            self.playback_thread.started.connect(self.playback_worker.run)
            self.playback_worker.data_received.connect(self.process_incoming_data)
            self.playback_worker.finished.connect(lambda: self.btn_playback.setText("MODE: PLAYBACK"))
            self.playback_thread.start()
            self.btn_playback.setText("STOP PLAYBACK")

    def save_current_config(self):
        """Menyimpan seluruh konfigurasi UI ke file JSON"""
        # 1. Kumpulkan Data Mapping Sensor
        # 2. Kumpulkan Daftar Grafik & Rumusnya
        graphs = []
        for i in range(self.graph_layout.count()):
            w = self.graph_layout.itemAt(i).widget()
            if isinstance(w, GraphWidget):
                graphs.append({"name": w.sensor_name, "formula": w.formula})

        # 3. Kumpulkan Tombol Perintah Custom
        commands = []
        for i in range(self.cmd_buttons_layout.count()):
            btn = self.cmd_buttons_layout.itemAt(i).widget()
            if isinstance(btn, QPushButton):
                commands.append(btn.text())

        config_data = {
            "baudrate": self.baud_combo.currentText(),
            "mapping": self.data_mapping,
            "graphs": graphs,
            "commands": commands,
            "primary_log": self.primary_path.text(),
            "redundant_log": self.redundant_path.text()
        }

        path, _ = QFileDialog.getSaveFileName(self, "Simpan Profile", "profiles/", "JSON (*.json)")
        if path:
            with open(path, 'w') as f:
                json.dump(config_data, f, indent=4)
            QMessageBox.information(self, "Sukses", "Konfigurasi berhasil disimpan!")

    def load_config_from_file(self):
        """Memuat konfigurasi dari JSON dan menerapkannya ke UI"""
        path, _ = QFileDialog.getOpenFileName(self, "Buka Profile", "profiles/", "JSON (*.json)")
        if not path: return

        try:
            with open(path, 'r') as f:
                config = json.load(f)

            # 1. Terapkan Baudrate & Path
            self.baud_combo.setCurrentText(config.get("baudrate", "115200"))
            self.primary_path.setText(config.get("primary_log", ""))
            self.redundant_path.setText(config.get("redundant_log", ""))

            # 2. Terapkan Data Mapping & Update Dashboard
            self.data_mapping = config.get("mapping", [])
            self.update_dashboard_ui()

            # 3. Rebuild Grafik
            # Hapus grafik lama
            while self.graph_layout.count():
                w = self.graph_layout.takeAt(0).widget()
                if w: w.deleteLater()
            
            # Tambah grafik baru dari profile
            for idx, g in enumerate(config.get("graphs", [])):
                new_g = GraphWidget(g['name'])
                new_g.formula = g['formula']
                self.graph_layout.addWidget(new_g, idx // 2, idx % 2)

            # 4. Rebuild Tombol Perintah
            while self.cmd_buttons_layout.count():
                w = self.cmd_buttons_layout.takeAt(0).widget()
                if w: w.deleteLater()
            
            for cmd in config.get("commands", []):
                color = "#800" if "IGNITE" in cmd else "#333"
                self.add_command_button(cmd, color)

            QMessageBox.information(self, "Sukses", "Konfigurasi berhasil dimuat!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal memuat profile: {e}")

class DataConfigDialog(QDialog):
    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.setWindowTitle("Konfigurasi Data")
        self.resize(400, 300)
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Indeks", "Nama", "Tipe"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        btns = QHBoxLayout()
        add = QPushButton("+"); add.clicked.connect(self.add_row); btns.addWidget(add)
        save = QPushButton("SIMPAN"); save.clicked.connect(self.accept); btns.addWidget(save)
        layout.addLayout(btns)
        if config:
            for c in config: self.add_row(c['name'], c['type'])

    def add_row(self, name="", dtype="Data"):
        row = self.table.rowCount(); self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(str(row)))
        self.table.setItem(row, 1, QTableWidgetItem(name))
        combo = QComboBox(); combo.addItems(["Data", "Status"]); combo.setCurrentText(dtype)
        self.table.setCellWidget(row, 2, combo)

    def get_config(self):
        config = []
        for r in range(self.table.rowCount()):
            config.append({
                "index": int(self.table.item(r, 0).text()),
                "name": self.table.item(r, 1).text(),
                "type": self.table.cellWidget(r, 2).currentText()
            })
        return config