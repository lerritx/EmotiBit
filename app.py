from flask import Flask, render_template, jsonify
from pythonosc import dispatcher
from pythonosc import osc_server
from threading import Thread
import queue
import datetime
import socket
import time
import atexit

app = Flask(__name__)

# คิวสำหรับเก็บข้อมูลจากเซ็นเซอร์
sensor_data = {
    'PPG_RED': queue.Queue(maxsize=100),
    'PPG_IR': queue.Queue(maxsize=100),
    'PPG_GRN': queue.Queue(maxsize=100),
    'EDA': queue.Queue(maxsize=100),
    'HUMIDITY': queue.Queue(maxsize=100),
    'ACC_X': queue.Queue(maxsize=100),
    'ACC_Y': queue.Queue(maxsize=100),
    'ACC_Z': queue.Queue(maxsize=100),
    'GYRO_X': queue.Queue(maxsize=100),
    'GYRO_Y': queue.Queue(maxsize=100),
    'GYRO_Z': queue.Queue(maxsize=100),
    'MAG_X': queue.Queue(maxsize=100),
    'MAG_Y': queue.Queue(maxsize=100),
    'MAG_Z': queue.Queue(maxsize=100),
    'TEMP': queue.Queue(maxsize=100),
}

# Global variable for OSC server
osc_server_instance = None


def process_osc_message(address, *args):
    """ฟังก์ชันสำหรับประมวลผลข้อมูลที่ได้จาก OSC"""
    sensor_type = address.split('/')[-1].replace(':', '_')
    if sensor_type in sensor_data:
        if sensor_data[sensor_type].full():
            sensor_data[sensor_type].get()
        sensor_data[sensor_type].put({
            'timestamp': datetime.datetime.now().strftime('%H:%M:%S'),
            'value': args[0]
        })


def is_port_in_use(port):
    """ตรวจสอบว่าพอร์ตถูกใช้งานอยู่หรือไม่"""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return False
        except OSError:
            return True


def find_available_port(start_port):
    """หาพอร์ตที่ว่างถัดไป"""
    port = start_port
    while is_port_in_use(port):
        port += 1
    return port


def start_osc_server():
    """เริ่ม OSC server"""
    global osc_server_instance

    # หาพอร์ตที่ว่าง
    port = find_available_port(3005)

    dispatcher_osc = dispatcher.Dispatcher()
    patches = [
        "/EmotiBit/0/PPG:RED",
        "/EmotiBit/0/PPG:IR",
        "/EmotiBit/0/PPG:GRN",
        "/EmotiBit/0/EDA",
        "/EmotiBit/0/HUMIDITY",
        "/EmotiBit/0/ACC:X",
        "/EmotiBit/0/ACC:Y",
        "/EmotiBit/0/ACC:Z",
        "/EmotiBit/0/GYRO:X",
        "/EmotiBit/0/GYRO:Y",
        "/EmotiBit/0/GYRO:Z",
        "/EmotiBit/0/MAG:X",
        "/EmotiBit/0/MAG:Y",
        "/EmotiBit/0/MAG:Z",
        "/EmotiBit/0/TEMP",
    ]

    for osc_address in patches:
        dispatcher_osc.map(osc_address, process_osc_message)

    try:
        osc_server_instance = osc_server.ThreadingOSCUDPServer(
            ("127.0.0.1", port),
            dispatcher_osc
        )
        print(f"OSC Server listening on 127.0.0.1:{port}")
        osc_server_instance.serve_forever()
    except Exception as e:
        print(f"Error starting OSC server: {e}")


def cleanup():
    """ทำความสะอาดเมื่อปิดโปรแกรม"""
    global osc_server_instance
    if osc_server_instance:
        print("Shutting down OSC server...")
        osc_server_instance.shutdown()
        osc_server_instance.server_close()


@app.route('/')
def index():
    """หน้าหลักของแอพพลิเคชัน"""
    return render_template('index.html')


@app.route('/data')
def get_data():
    """API endpoint สำหรับดึงข้อมูลเซ็นเซอร์"""
    current_data = {}
    for sensor_type, q in sensor_data.items():
        current_data[sensor_type] = list(q.queue)
    return jsonify(current_data)


if __name__ == '__main__':
    # ลงทะเบียนฟังก์ชัน cleanup
    atexit.register(cleanup)

    # เริ่ม OSC server ในอีก thread
    osc_thread = Thread(target=start_osc_server)
    osc_thread.daemon = True
    osc_thread.start()

    # รอให้ OSC server เริ่มทำงาน
    time.sleep(1)

    # เริ่ม Flask app โดยปิด debug mode
    app.run(debug=False, port=5000)