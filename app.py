from flask import Flask, render_template, Response, request,redirect,url_for
import sqlite3
app = Flask(__name__)

@app.route('/')
def upload_video():
    # create_db()
    return render_template('home.html')

# def create_db():
#     conn = sqlite3.connect('database.db')

#     conn.execute("""CREATE TABLE IF NOT EXISTS videos(
#                  id INTEGER PRIMARY KEY AUTOINCREMENT, 
#                  original_video_path TEXT, 
#                  annotated_video_path TEXT, 
#                  uploaded_at TIMESTEMP DEFAULT CURRENT_TIMESTAMP);
#                  """)
#     conn.commit()
#     conn.close()



def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn



from ultralytics import YOLO
import cv2
import os
import time

model = YOLO('./freeze_whitecane.pt')

def generate_frames(video_list, output_list):
    
    for idx, video_path in enumerate(video_list):
        cap = cv2.VideoCapture(video_path)
        output_path = output_list[idx]

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        if not cap.isOpened():
            print(f'비디오 리스트 오류:{video_path}')
        
        while cap.isOpened():
            ret , frame = cap.read()

            if not ret:
                print('스트리밍 종료')
                time.sleep(2)     
                yield (b'--frame\r\n'
                       b'Content-Type : text/plain\r\n\r\n'+b'END\r\n')
                break

            results = model(frame)

            if results:
                result = results[0]
                annotated_frame = result.plot()
                out.write(annotated_frame)

                ret, buffer = cv2.imencode('.jpg', annotated_frame)
                frame = buffer.tobytes()

                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        cap.release()
        out.release()

    print('스트리밍 완료')
    yield (b'--frame\r\n'
        b'Content-Type: text/html\r\n\r\n'
        b'<html><body><h1>streaming done</h1>\r\n'
        b'<script>\r\n'
        b'setTimeout(function(){window.location.href="/";}, 2000);'  # 2초 후 리다이렉트
        b'</script>\r\n'
        b'</body></html>\r\n')



from datetime import datetime
import glob


@app.route('/annotated_video/', methods=['POST'])
def annotated_video():
    
    video_list = glob.glob('video/test/*.mp4')
    output_list = []

    for video_path in video_list:
        video_name = os.path.basename(video_path)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_path = os.path.join('video/annotated_video', f'output_{video_name}_{timestamp}.mp4')
        output_list.append(output_path)

        conn = get_db_connection()
        conn.execute("""INSERT INTO videos (original_video_path, annotated_video_path)
                            VALUES (?,?)""", (video_path, output_path))
        conn.commit()
        conn.close()

    # stream_videos(video_list,output_list)
    return Response(generate_frames(video_list, output_list), mimetype='multipart/x-mixed-replace; boundary=frame')
    


def stream_videos(video_list, output_list):
    return Response(generate_frames(video_list, output_list), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/annotated_video_done')
def annotated_video_done():
    return redirect(url_for('upload_video'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)