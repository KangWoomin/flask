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


model = YOLO('./freeze_whitecane.pt')

def generate_frames(video_path, outpu_path):
    cap = cv2.VideoCapture(video_path)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out = cv2.VideoWriter(outpu_path, fourcc, fps, (width, height))
    
    if not cap.isOpened():
        return 
    
    while cap.isOpened():
        ret, frame = cap.read()

        if not ret:
            break

        results = model(frame)

        if results:
            result = results[0]
            annotated_frame = result.plot()
            out.write(annotated_frame)

            ret, buffer = cv2.imencode('.jpg', annotated_frame)
            frame = buffer.tobytes()            

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n'+frame+b'\r\n')

    cap.release()
    out.release()
    cv2.destroyAllWindows()

    # 영상 끝날 때 종료 신호 전송
    yield (b'--frame\r\n'
           b'Content-Type: text/plain\r\n\r\nEND\r\n')


from datetime import datetime
@app.route('/annotated_video/', methods=['POST'])
def annotated_video():

    if 'video' not in request.files:
        return redirect(url_for('upload_video'))
    
    video_file = request.files['video']
    if video_file.filename =='':
        return redirect(url_for('upload_video'))
    
    video_name = video_file.filename
    video_path = os.path.join('video', video_name)
    video_file.save(video_path)

    output_path = os.path.join('video/annotated_video',f'output_{video_name}_{datetime.now()}')

    conn = get_db_connection()
    conn.execute("INSERT INTO videos (original_video_path, annotated_video_path) VALUES(?,?)",
                 (video_path, output_path))
    conn.commit()
    conn.close()
    
    return Response(generate_frames(video_path, output_path), mimetype='multipart/x-mixed-replace; boundary=frame')






if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)