import streamlit as st
from services.auth.login_wall import render_login_wall
from services.state.session_defaults import initialize_session_defaults
from services.config.workout_config import EXERCISE_OPTIONS
import os
import time
from services.ui.style_loader import load_css, inject_local_font, inject_webrtc_styles 
from services.persistence.exercise_repository import init_db
from streamlit_webrtc import webrtc_streamer, WebRtcMode
from services.vision.exercise_video_processor import VideoProcessorClass
from services.tracking.metrics import sync_metrics_update
from services.persistence.exercise_repository import get_users_exercises
import pandas as pd

# st.title("StayFit : AI Gym Coach")
# st.write("Welcome to StayFit! Login to start your fitness journey.")

def main():
    st.set_page_config(
        page_title="StayFit : AI Gym Coach",
        page_icon="💪",
        layout="centered",
        initial_sidebar_state="expanded",

    )
    
    load_css(os.path.join(os.getcwd(), "static", "style.css"))
    inject_local_font(os.path.join(os.getcwd(), "static", "AdobeClean.otf"), "AdobeClean")
    init_db()
    
    if not render_login_wall():
        return
    
    initialize_session_defaults()
    workout_started = st.session_state.get("workout_started", False)
    
    with st.sidebar:
        st.title("StayFit : AI Gym Coach")
        st.write(f"👤 Logged in as: {st.session_state.get('username', 'Unknown User')}")
    
        st.divider()
        
        if not workout_started:
            plan_exercise = st.selectbox("Select Exercise", options=EXERCISE_OPTIONS, key="plan_exercise")
            plan_sets = st.number_input("Target Sets", min_value=1, max_value=10, value=3, step=1, key="plan_sets")
            plan_reps = st.number_input("Reps per Set", min_value=1, max_value=50, value=10, step=1, key="plan_reps")
            start_session_button = st.button("Start Workout", key="start_workout_button", width="stretch")
            
            if start_session_button:
                st.session_state.exercise_type = plan_exercise
                st.session_state.target_sets = int(plan_sets)
                st.session_state.reps_per_set = int(plan_reps)
                st.session_state.reps = 0
                st.session_state.workout_started = True
                st.session_state.set_cycle_started_at = time.time()
                st.session_state.last_saved_sets_completed = 0
                st.session_state.last_modified_sets_completed = 0
                st.session_state.last_saved_workout_completed = 0
                st.rerun()
        else: 
            st.write("Workout started! Keep going!")
            exercise = st.session_state.get("plan_exercise")
            sets = st.session_state.get("plan_sets")
            reps = st.session_state.get("plan_reps")
            
            st.info(f"**{exercise}** - {sets} Sets/{reps} Reps")
            
            end_workout_button = st.button("End Workout", key="end_workout_button", width="stretch")
            
            if end_workout_button:
                st.session_state["workout_started"] = False
                # st.success("Workout session ended!")
                st.rerun()
        
        if workout_started:
            st.divider()
            st.write("### Progress")
            
            exercise = st.session_state.get("exercise_type")
            current_set_reps = st.session_state.get("current_set_reps", 0)
            reps_per_set = st.session_state.get("reps_per_set", 0)
            total_reps = st.session_state.get("reps", 0)
            sets_completed = st.session_state.get("sets_completed", 0)
            target_sets = st.session_state.get("target_sets", 0)
            
            st.metric(label="Total Reps", value=total_reps)
            st.metric(label="Current Set Reps", value=f"{current_set_reps}/{reps_per_set}")
            st.metric(label="Sets Completed", value=f"{sets_completed}/{target_sets}")
            
            st.divider()
            if exercise == "Squats":
                st.subheader("Squat Metrics")
                st.metric("Knee Angle", f"{st.session_state.knee_angle}°")
                st.metric("Back Angle", f"{st.session_state.back_angle}°")
                st.metric("Depth Status", st.session_state.depth_status)

            elif exercise == "Push-ups":
                st.subheader("Push-up Metrics")
                st.metric("Elbow Angle", f"{st.session_state.elbow_angle}°")
                st.metric("Body Alignment", st.session_state.body_alignment)
                st.metric("Hip Position", st.session_state.hip_status)

            elif exercise == "Biceps Curls":
                st.subheader("Curl Metrics")
                st.metric("Elbow Angle", f"{st.session_state.elbow_angle}°")
                st.metric("Elbow Stability", st.session_state.Elbow_status)
                st.metric("Swing Detection", st.session_state.swing_status)

            elif exercise == "Shoulder Press":
                st.subheader("Shoulder Press Metrics")
                st.metric("Elbow Angle", f"{st.session_state.elbow_angle}°")
                st.metric("Arm Extension", st.session_state.extension_status)
                st.metric("Back Arch", st.session_state.back_arch_status)

            elif exercise == "Lunges":
                st.subheader("Lunge Metrics")
                st.metric("Front Knee Angle", f"{st.session_state.front_knee_angle}°")
                st.metric("Torso Angle", f"{st.session_state.torso_angle}°")
                st.metric("Balance Status", st.session_state.balance_status)
    
    
    # Video Feature
    st.title("StayFit - Your AI Gym Coach")
    st.markdown("Powered by AI, Driven by You 😉")

    if not workout_started:
        st.markdown(
            """
            <div style="
                border: 10px dashed #444;
                border-radius: 0px;
                padding: 48px 32px;
                text-align: center;
                color: #888;
                margin-top: 32px;
                margin-bottom: 32px;
            ">
                <h2 style="color:#ccc; margin-bottom:8px;">👈 Set your workout plan</h2>
                <p style="font-size:1.05rem;">
                    Choose your exercise, sets and reps in the sidebar,<br>
                    then click <strong>"Start Workout"</strong> to activate the camera and AI coach.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        context = webrtc_streamer(
            key="exercise-analysis",
            mode=WebRtcMode.SENDRECV,
            media_stream_constraints= {
                "video": True,
                "audio": False
            },
            async_processing=True,   # Enable async processing for better performance
            video_processor_factory=VideoProcessorClass,
            rtc_configuration = {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            
        )
        
        sync_metrics_update(context)
        
        if context.state.playing:
            time.sleep(0.25)
            st.rerun()
            
        inject_webrtc_styles()
        
        st.divider()
        st.subheader("Workout History")
        
        user_id = st.session_state.get("user_id", 0)

        if isinstance(user_id, int):
            history_rows = get_users_exercises(user_id)

            df_arr = [
                {
                    "Exercise": row["exercise_name"],
                    "Reps": row["reps"],
                    "Sets": row["sets"],
                    "Time (sec)": row["time"],
                    "Date": row["created_at"]
                }
                for row in history_rows
            ]

            # create dataframe of fetched workout history
            df = pd.DataFrame(df_arr)

            if not df.empty:
                df["Date"] = pd.to_datetime(df["Date"]).dt.date     # chage date format
                agg_df = df.groupby(["Exercise", "Date"]).agg(      # aggregate history for same day , same exercise
                    {
                        'Reps': 'sum',
                        "Sets": 'sum',
                        "Time (sec)": 'sum'
                    }
                ).reset_index()
                agg_df.index += 1       # index start from 0 -> +1 
                
                st.table(agg_df, border="horizontal")   # displays table from dataframe
            else:
                st.info("No workout history found.")
            

        
if __name__ == "__main__":
    main()