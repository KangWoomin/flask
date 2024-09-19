from flask import Flask, render_template, Response, request,redirect,url_for

app = Flask(__name__)

@app.route('/')
def upload_video():
    return render_template('home.html')



from ultralytics import YOLO
import cv2
import os


model = YOLO('./don`t_freeze_whitecane.pt')

def generate_frames(video_path, outpu_path):
    cap = cv2.VideoCapture(video_path)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out = cv2.VideoWriter(outpu_path, fourcc, fps, (width, height))

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

    output_path = os.path.join('video',f'output_{video_name}')
    #영상 끝나고 나서 다시 upload_video.html으로 돌아가게 구현 필요
    return Response(generate_frames(video_path, output_path), mimetype='multipart/x-mixed-replace; boundary=frame')






if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)