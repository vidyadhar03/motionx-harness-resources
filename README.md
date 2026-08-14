cd ~/motionx-spike
source .venv/bin/activate
export GEMINI_API_KEY=AIzaSyC4Zucp4Nl80NSdLOjaHRv4KFf6N3VrZ-s
export GOOGLE_APPLICATION_CREDENTIALS="/Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/serviceAccountKey.json"

python agent_gemini.py "Break scene 2 into a shot list. Write each shot to the tree."