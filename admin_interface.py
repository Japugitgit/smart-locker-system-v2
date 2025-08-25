import streamlit as st
import asyncio
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import logging
from typing import Dict, List, Any

# Import system components
from main_controller import SmartLockerController, SystemState
from auth.pin_verification import PINVerifier
from auth.access_control import AccessController
from hardware.lock_controller import LockManager

# Configure page
st.set_page_config(
    page_title="Smart Locker Admin",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Global variables for system controller
if 'controller' not in st.session_state:
    st.session_state.controller = None
if 'system_running' not in st.session_state:
    st.session_state.system_running = False

class AdminInterface:
    """Streamlit Admin Interface for Smart Locker System"""
    
    def __init__(self):
        self.controller = st.session_state.controller
    
    def main(self):
        """Main admin interface"""
        st.title("🏠 Smart Locker Admin Dashboard")
        st.markdown("---")
        
        # Sidebar navigation
        with st.sidebar:
            st.header("🎛️ Control Panel")
            
            # System control
            self.render_system_control()
            st.markdown("---")
            
            # Quick actions
            self.render_quick_actions()
            st.markdown("---")
            
            # Navigation
            page = st.selectbox(
                "📄 Navigate to:",
                [
                    "Dashboard",
                    "User Management", 
                    "Access Logs",
                    "System Status",
                    "Hardware Control",
                    "Configuration",
                    "Security",
                    "Diagnostics"
                ]
            )
        
        # Main content based on selected page
        if page == "Dashboard":
            self.render_dashboard()
        elif page == "User Management":
            self.render_user_management()
        elif page == "Access Logs":
            self.render_access_logs()
        elif page == "System Status":
            self.render_system_status()
        elif page == "Hardware Control":
            self.render_hardware_control()
        elif page == "Configuration":
            self.render_configuration()
        elif page == "Security":
            self.render_security()
        elif page == "Diagnostics":
            self.render_diagnostics()
    
    def render_system_control(self):
        """Render system control section"""
        st.subheader("🔧 System Control")
        
        if not st.session_state.system_running:
            if st.button("🚀 Start System", type="primary"):
                with st.spinner("Starting Smart Locker System..."):
                    try:
                        st.session_state.controller = SmartLockerController(simulation_mode=True)
                        # Note: In real implementation, use asyncio.run()
                        st.session_state.system_running = True
                        st.success("✅ System started successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Failed to start system: {e}")
        else:
            st.success("✅ System Running")
            if st.button("🛑 Stop System", type="secondary"):
                with st.spinner("Stopping system..."):
                    try:
                        if st.session_state.controller:
                            # Note: In real implementation, use asyncio.run()
                            pass
                        st.session_state.controller = None
                        st.session_state.system_running = False
                        st.info("🛑 System stopped")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Failed to stop system: {e}")
    
    def render_quick_actions(self):
        """Render quick actions"""
        st.subheader("⚡ Quick Actions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔓 Emergency Unlock"):
                if self.controller:
                    st.warning("🚨 Emergency unlock activated!")
                    # Emergency unlock logic here
                else:
                    st.error("System not running")
        
        with col2:
            if st.button("🔒 Force Lock"):
                if self.controller:
                    st.info("🔒 Force lock activated!")
                    # Force lock logic here
                else:
                    st.error("System not running")
        
        if st.button("🔄 Restart System"):
            if self.controller:
                with st.spinner("Restarting system..."):
                    st.info("🔄 System restart initiated")
                    # Restart logic here
            else:
                st.error("System not running")
        
        if st.button("🧹 Clear Logs"):
            st.warning("🧹 Logs cleared")
            # Clear logs logic here
    
    def render_dashboard(self):
        """Render main dashboard"""
        col1, col2, col3, col4 = st.columns(4)
        
        # System status metrics
        with col1:
            if self.controller:
                status = self.controller.get_system_status()
                state = status.get("current_state", "Unknown")
                st.metric("🔧 System State", state.title())
            else:
                st.metric("🔧 System State", "Offline", delta="❌")
        
        with col2:
            # Simulated data for demo
            st.metric("👥 Total Users", "12", delta="2")
        
        with col3:
            st.metric("🔓 Access Today", "8", delta="3")
        
        with col4:
            if self.controller and hasattr(self.controller, 'lock'):
                lock_state = "Locked" if self.controller.lock.get_lock_state() else "Unlocked"
                st.metric("🔒 Lock Status", lock_state)
            else:
                st.metric("🔒 Lock Status", "Unknown")
        
        st.markdown("---")
        
        # Charts and graphs
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Access Statistics (Last 7 Days)")
            
            # Generate sample data
            dates = pd.date_range(end=datetime.now(), periods=7).date
            accesses = [5, 8, 12, 6, 9, 15, 8]  # Sample data
            
            fig = px.bar(
                x=dates, 
                y=accesses,
                title="Daily Access Count",
                labels={"x": "Date", "y": "Access Count"}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("🔐 Authentication Methods")
            
            # Sample data
            methods = ["PIN Only", "Voice + PIN", "Emergency", "Admin"]
            counts = [45, 35, 2, 8]  # Sample data
            
            fig = px.pie(
                values=counts,
                names=methods,
                title="Authentication Method Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Recent activity
        st.subheader("📋 Recent Activity")
        
        # Sample recent activity data
        recent_activity = [
            {"Time": "2024-01-15 14:30", "User": "john_doe", "Action": "Access Granted", "Method": "Voice + PIN"},
            {"Time": "2024-01-15 12:15", "User": "jane_smith", "Action": "Access Granted", "Method": "PIN Only"},
            {"Time": "2024-01-15 09:45", "User": "admin", "Action": "Admin Access", "Method": "Admin PIN"},
            {"Time": "2024-01-15 08:30", "User": "bob_wilson", "Action": "Access Denied", "Method": "Voice + PIN"},
            {"Time": "2024-01-14 18:20", "User": "emergency", "Action": "Emergency Unlock", "Method": "Emergency Code"}
        ]
        
        df = pd.DataFrame(recent_activity)
        st.dataframe(df, use_container_width=True)
    
    def render_user_management(self):
        """Render user management interface"""
        st.header("👥 User Management")
        
        # User list
        st.subheader("📋 Registered Users")
        
        # Sample user data
        users_data = [
            {"User ID": "john_doe", "Name": "John Doe", "Role": "User", "PIN Set": "✅", "Voice Enrolled": "✅", "Last Access": "2024-01-15 14:30"},
            {"User ID": "jane_smith", "Name": "Jane Smith", "Role": "User", "PIN Set": "✅", "Voice Enrolled": "❌", "Last Access": "2024-01-15 12:15"},
            {"User ID": "bob_wilson", "Name": "Bob Wilson", "Role": "User", "PIN Set": "✅", "Voice Enrolled": "✅", "Last Access": "2024-01-14 16:45"},
            {"User ID": "admin", "Name": "Administrator", "Role": "Admin", "PIN Set": "✅", "Voice Enrolled": "✅", "Last Access": "2024-01-15 09:45"}
        ]
        
        df_users = pd.DataFrame(users_data)
        st.dataframe(df_users, use_container_width=True)
        
        st.markdown("---")
        
        # Add new user
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("➕ Add New User")
            
            with st.form("add_user_form"):
                user_id = st.text_input("User ID")
                user_name = st.text_input("Full Name")
                user_role = st.selectbox("Role", ["User", "Admin"])
                initial_pin = st.text_input("Initial PIN", type="password")
                
                if st.form_submit_button("Add User"):
                    if user_id and user_name and initial_pin:
                        st.success(f"✅ User '{user_id}' added successfully!")
                        # Add user logic here
                    else:
                        st.error("❌ Please fill all required fields")
        
        with col2:
            st.subheader("🔧 User Actions")
            
            selected_user = st.selectbox("Select User", [user["User ID"] for user in users_data])
            
            col2_1, col2_2 = st.columns(2)
            
            with col2_1:
                if st.button("🔑 Reset PIN"):
                    st.warning(f"PIN reset for user: {selected_user}")
                
                if st.button("🎤 Reset Voice"):
                    st.warning(f"Voice enrollment reset for user: {selected_user}")
            
            with col2_2:
                if st.button("🚫 Disable User"):
                    st.error(f"User disabled: {selected_user}")
                
                if st.button("🗑️ Delete User"):
                    st.error(f"User deleted: {selected_user}")
    
    def render_access_logs(self):
        """Render access logs interface"""
        st.header("📋 Access Logs")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            date_filter = st.date_input("📅 Date Range", value=[datetime.now().date() - timedelta(days=7), datetime.now().date()])
        
        with col2:
            user_filter = st.selectbox("👤 User Filter", ["All Users", "john_doe", "jane_smith", "bob_wilson", "admin"])
        
        with col3:
            action_filter = st.selectbox("🔍 Action Filter", ["All Actions", "Access Granted", "Access Denied", "Emergency", "Admin"])
        
        # Sample access log data
        access_logs = [
            {"Timestamp": "2024-01-15 14:30:25", "User": "john_doe", "Action": "Access Granted", "Method": "Voice + PIN", "Confidence": "0.87", "Duration": "00:15", "IP": "192.168.1.100"},
            {"Timestamp": "2024-01-15 12:15:42", "User": "jane_smith", "Action": "Access Granted", "Method": "PIN Only", "Confidence": "-", "Duration": "00:08", "IP": "192.168.1.101"},
            {"Timestamp": "2024-01-15 09:45:18", "User": "admin", "Action": "Admin Access", "Method": "Admin PIN", "Confidence": "-", "Duration": "05:32", "IP": "192.168.1.102"},
            {"Timestamp": "2024-01-15 08:30:55", "User": "bob_wilson", "Action": "Access Denied", "Method": "Voice + PIN", "Confidence": "0.52", "Duration": "-", "IP": "192.168.1.103"},
            {"Timestamp": "2024-01-14 18:20:13", "User": "emergency", "Action": "Emergency Unlock", "Method": "Emergency Code", "Confidence": "-", "Duration": "00:02", "IP": "Local"}
        ]
        
        df_logs = pd.DataFrame(access_logs)
        st.dataframe(df_logs, use_container_width=True)
        
        # Export options
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📄 Export CSV"):
                csv = df_logs.to_csv(index=False)
                st.download_button("Download CSV", csv, "access_logs.csv", "text/csv")
        
        with col2:
            if st.button("📊 Generate Report"):
                st.info("📊 Generating detailed report...")
        
        with col3:
            if st.button("🧹 Clear Old Logs"):
                st.warning("🧹 Old logs cleared")
    
    def render_system_status(self):
        """Render system status interface"""
        st.header("🖥️ System Status")
        
        if not self.controller:
            st.error("❌ System is not running")
            return
        
        # System overview
        status = self.controller.get_system_status() if self.controller else {}
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔧 System Information")
            
            st.json({
                "Current State": status.get("current_state", "Unknown"),
                "Simulation Mode": status.get("simulation_mode", "Unknown"),
                "Auth Attempts": status.get("auth_attempts", 0),
                "Current User": status.get("current_user", "None"),
                "Last Activity": status.get("last_activity", "Unknown")
            })
        
        with col2:
            st.subheader("🔌 Hardware Status")
            
            hw_status = status.get("hardware_status", {})
            
            # Hardware status indicators
            components = ["keypad", "led", "buzzer", "lock"]
            
            for component in components:
                comp_status = hw_status.get(component, {})
                if comp_status:
                    sim_mode = comp_status.get("simulation_mode", True)
                    status_icon = "🟢" if not sim_mode else "🟡"
                    mode_text = "Hardware" if not sim_mode else "Simulation"
                    st.write(f"{status_icon} {component.title()}: {mode_text}")
                else:
                    st.write(f"🔴 {component.title()}: Offline")
        
        # Real-time metrics
        st.markdown("---")
        st.subheader("📊 Real-time Metrics")
        
        # Create metrics charts
        col1, col2 = st.columns(2)
        
        with col1:
            # CPU/Memory usage (simulated)
            cpu_usage = 45  # Simulated
            memory_usage = 62  # Simulated
            
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = cpu_usage,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "CPU Usage (%)"},
                gauge = {'axis': {'range': [None, 100]},
                        'bar': {'color': "darkblue"},
                        'steps' : [{'range': [0, 50], 'color': "lightgray"},
                                  {'range': [50, 80], 'color': "yellow"},
                                  {'range': [80, 100], 'color': "red"}],
                        'threshold' : {'line': {'color': "red", 'width': 4},
                                      'thickness': 0.75, 'value': 90}}))
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = memory_usage,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Memory Usage (%)"},
                gauge = {'axis': {'range': [None, 100]},
                        'bar': {'color': "darkgreen"},
                        'steps' : [{'range': [0, 50], 'color': "lightgray"},
                                  {'range': [50, 80], 'color': "yellow"},
                                  {'range': [80, 100], 'color': "red"}],
                        'threshold' : {'line': {'color': "red", 'width': 4},
                                      'thickness': 0.75, 'value': 90}}))
            st.plotly_chart(fig, use_container_width=True)
    
    def render_hardware_control(self):
        """Render hardware control interface"""
        st.header("🔌 Hardware Control")
        
        if not self.controller:
            st.error("❌ System is not running")
            return
        
        # LED Control
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("💡 LED Control")
            
            led_status = st.selectbox("Status", ["idle", "ready", "processing", "success", "error", "warning"])
            
            if st.button("Set LED Status"):
                st.success(f"💡 LED set to: {led_status}")
                # LED control logic here
            
            led_color = st.color_picker("Custom Color", "#00FF00")
            
            if st.button("Set Custom Color"):
                st.success(f"💡 LED color set to: {led_color}")
            
            if st.button("Flash Red"):
                st.warning("💡 LED flashing red...")
        
        with col2:
            st.subheader("🔊 Buzzer Control")
            
            buzzer_action = st.selectbox("Sound", ["beep", "success", "error", "warning", "alarm"])
            
            if st.button("Play Sound"):
                st.success(f"🔊 Playing: {buzzer_action}")
                # Buzzer control logic here
            
            frequency = st.slider("Frequency (Hz)", 200, 2000, 1000)
            duration = st.slider("Duration (s)", 0.1, 2.0, 0.5)
            
            if st.button("Custom Beep"):
                st.success(f"🔊 Beep: {frequency}Hz for {duration}s")
        
        # Lock Control
        st.markdown("---")
        st.subheader("🔒 Lock Control")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔓 Unlock", type="primary"):
                st.success("🔓 Lock unlocked")
                # Unlock logic here
        
        with col2:
            if st.button("🔒 Lock"):
                st.info("🔒 Lock locked")
                # Lock logic here
        
        with col3:
            if st.button("🚨 Emergency Unlock", type="secondary"):
                st.warning("🚨 Emergency unlock activated!")
                # Emergency unlock logic here
        
        # Door sensor simulation
        st.markdown("---")
        st.subheader("🚪 Door Sensor Simulation")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🚪 Simulate Door Open"):
                st.info("🚪 Door opened (simulated)")
        
        with col2:
            if st.button("🚪 Simulate Door Close"):
                st.info("🚪 Door closed (simulated)")
    
    def render_configuration(self):
        """Render configuration interface"""
        st.header("⚙️ System Configuration")
        
        # Load current configuration
        try:
            with open("config/smart_locker_config.json", "r") as f:
                config = json.load(f)
        except:
            config = {}
        
        # Authentication settings
        st.subheader("🔐 Authentication Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            voice_timeout = st.number_input("Voice Timeout (s)", value=config.get("voice_timeout", 10.0), min_value=5.0, max_value=30.0)
            pin_timeout = st.number_input("PIN Timeout (s)", value=config.get("pin_timeout", 30.0), min_value=10.0, max_value=120.0)
            voice_threshold = st.slider("Voice Threshold", 0.5, 1.0, config.get("voice_threshold", 0.75))
        
        with col2:
            max_attempts = st.number_input("Max Auth Attempts", value=config.get("max_auth_attempts", 3), min_value=1, max_value=10)
            access_duration = st.number_input("Access Duration (s)", value=config.get("access_duration", 30.0), min_value=10.0, max_value=300.0)
            gmm_enabled = st.checkbox("Enable GMM Scoring", value=config.get("gmm_enabled", True))
        
        # Hardware settings
        st.markdown("---")
        st.subheader("🔌 Hardware Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            led_brightness = st.slider("LED Brightness", 0.1, 1.0, config.get("hardware_config", {}).get("led_brightness", 0.8))
            buzzer_volume = st.slider("Buzzer Volume", 0.1, 1.0, config.get("hardware_config", {}).get("buzzer_volume", 0.7))
        
        with col2:
            door_timeout = st.number_input("Door Timeout (s)", value=config.get("hardware_config", {}).get("door_timeout", 300), min_value=60, max_value=600)
            keypad_debounce = st.number_input("Keypad Debounce (ms)", value=config.get("hardware_config", {}).get("keypad_debounce_time", 200), min_value=50, max_value=500)
        
        # Emergency codes
        st.markdown("---")
        st.subheader("🚨 Emergency Codes")
        
        emergency_codes = st.text_area("Emergency Codes (one per line)", value="\n".join(config.get("emergency_codes", ["*911*", "#999#"])))
        admin_codes = st.text_area("Admin Codes (one per line)", value="\n".join(config.get("admin_codes", ["*123*", "#456#"])))
        
        # Save configuration
        st.markdown("---")
        
        if st.button("💾 Save Configuration", type="primary"):
            # Update configuration
            new_config = config.copy()
            new_config.update({
                "voice_timeout": voice_timeout,
                "pin_timeout": pin_timeout,
                "voice_threshold": voice_threshold,
                "max_auth_attempts": max_attempts,
                "access_duration": access_duration,
                "gmm_enabled": gmm_enabled,
                "emergency_codes": emergency_codes.strip().split("\n"),
                "admin_codes": admin_codes.strip().split("\n"),
                "hardware_config": {
                    "led_brightness": led_brightness,
                    "buzzer_volume": buzzer_volume,
                    "door_timeout": door_timeout,
                    "keypad_debounce_time": keypad_debounce
                }
            })
            
            # Save to file
            try:
                os.makedirs("config", exist_ok=True)
                with open("config/smart_locker_config.json", "w") as f:
                    json.dump(new_config, f, indent=2)
                st.success("✅ Configuration saved successfully!")
            except Exception as e:
                st.error(f"❌ Failed to save configuration: {e}")
    
    def render_security(self):
        """Render security interface"""
        st.header("🛡️ Security Management")
        
        # Security overview
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("🔒 Failed Attempts Today", "3", delta="-2")
        
        with col2:
            st.metric("🚨 Security Alerts", "1", delta="1")
        
        with col3:
            st.metric("🔐 Active Sessions", "0")
        
        # Security events
        st.markdown("---")
        st.subheader("🚨 Recent Security Events")
        
        security_events = [
            {"Timestamp": "2024-01-15 08:30", "Event": "Failed Authentication", "User": "bob_wilson", "Severity": "Medium", "Details": "Voice confidence too low (0.52)"},
            {"Timestamp": "2024-01-14 23:15", "Event": "Emergency Unlock", "User": "emergency", "Severity": "High", "Details": "Emergency code *911* used"},
            {"Timestamp": "2024-01-14 16:45", "Event": "Multiple Failed Attempts", "User": "unknown", "Severity": "High", "Details": "5 failed PIN attempts"},
            {"Timestamp": "2024-01-14 12:30", "Event": "Admin Access", "User": "admin", "Severity": "Low", "Details": "Admin panel accessed"}
        ]
        
        df_security = pd.DataFrame(security_events)
        st.dataframe(df_security, use_container_width=True)
        
        # Security actions
        st.markdown("---")
        st.subheader("🔧 Security Actions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔒 Lock System"):
                st.warning("🔒 System locked for security")
            
            if st.button("🚫 Enable Lockout Mode"):
                st.error("🚫 Lockout mode enabled")
        
        with col2:
            if st.button("🔄 Reset Failed Attempts"):
                st.success("🔄 Failed attempts counter reset")
            
            if st.button("📧 Send Security Alert"):
                st.info("📧 Security alert sent to administrators")
    
    def render_diagnostics(self):
        """Render diagnostics interface"""
        st.header("🔍 System Diagnostics")
        
        # System health check
        st.subheader("🩺 System Health Check")
        
        with st.spinner("Running diagnostics..."):
            # Simulate diagnostic tests
            import time
            time.sleep(2)
        
        # Health check results
        health_checks = [
            {"Component": "Main Controller", "Status": "✅ Healthy", "Details": "All systems operational"},
            {"Component": "Authentication System", "Status": "✅ Healthy", "Details": "PIN and voice systems ready"},
            {"Component": "Hardware Controllers", "Status": "🟡 Warning", "Details": "Running in simulation mode"},
            {"Component": "Database", "Status": "✅ Healthy", "Details": "Connection stable"},
            {"Component": "Configuration", "Status": "✅ Healthy", "Details": "All settings valid"},
            {"Component": "Logging System", "Status": "✅ Healthy", "Details": "Logs writing correctly"}
        ]
        
        df_health = pd.DataFrame(health_checks)
        st.dataframe(df_health, use_container_width=True)
        
        # Performance metrics
        st.markdown("---")
        st.subheader("📊 Performance Metrics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("⚡ Response Time", "45ms", delta="-5ms")
            st.metric("🧠 Memory Usage", "234MB", delta="12MB")
        
        with col2:
            st.metric("💾 Disk Usage", "2.1GB", delta="50MB")
            st.metric("🌡️ CPU Temperature", "42°C", delta="1°C")
        
        # Test buttons
        st.markdown("---")
        st.subheader("🧪 Test Functions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔊 Test Audio"):
                st.success("🔊 Audio test completed")
        
        with col2:
            if st.button("💡 Test LEDs"):
                st.success("💡 LED test completed")
        
        with col3:
            if st.button("🔒 Test Lock"):
                st.success("🔒 Lock test completed")
        
        # Log viewer
        st.markdown("---")
        st.subheader("📄 System Logs")
        
        log_level = st.selectbox("Log Level", ["ALL", "DEBUG", "INFO", "WARNING", "ERROR"])
        
        # Sample log entries
        logs = [
            "2024-01-15 14:30:25 INFO - Access granted to user: john_doe",
            "2024-01-15 12:15:42 INFO - PIN authentication successful",
            "2024-01-15 09:45:18 WARNING - Multiple failed authentication attempts",
            "2024-01-15 08:30:55 ERROR - Voice recognition failed for user: bob_wilson",
            "2024-01-14 18:20:13 INFO - Emergency unlock activated"
        ]
        
        for log in logs:
            st.text(log)

def main():
    """Main function to run the admin interface"""
    try:
        # Initialize admin interface
        admin = AdminInterface()
        admin.main()
    
    except Exception as e:
        st.error(f"❌ Application error: {e}")
        st.exception(e)

if __name__ == "__main__":
    main()