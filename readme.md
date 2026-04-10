🩺 Pinball Doctor
 is an AI-powered diagnostic tool for pinball technicians. It combines factory documentation, community forum wisdom, and advanced computer vision to help you solve repair issues faster.

🌐 Live Web App
Access the tool directly in your browser:
pinball-doctor.streamlit.app

🛠️ Under the Hood: The "Trinity" of Data
Unlike general AI, the Doctor cross-references three specific layers of data for every diagnosis:

Technical Wiki Data: Pulls deep system-architecture specs from PinWiki (voltages, board revisions, component locations).

Community Wisdom: Searches the Pinside Tech Forums for real-world "field fixes" and solutions from the technician community.

Factory Documentation: Automatically looks for manual and schematic links on IPDB to ensure factory-standard accuracy.

📖 How to Use
Unlock: Enter the Tech Password in the sidebar to enable the diagnostic engine.

Diagnose: Type your machine name and the symptom in the chat box.

Example: "Gorgar - display is flickering"

Example: "Cactus Jack's - sound is distorted"

Vision Analysis: Use the Upload button in the sidebar to snap a photo of a circuit board or a schematic scan. Ask the Doctor: "Looking at this photo, do any of these capacitors look leaked?" or "Trace the 5V path on this schematic."

Interactive Repair: The Doctor remembers your conversation. If a fix fails, simply say: "I tried that and it didn't work, what's next?"

🔒 Security & Privacy
Access Control: Restricted via a Tech Password to manage API usage and protect the developer's credentials.

Ephemeral Sessions: Your photos and chat history are not stored permanently; refreshing the page or starting a "New Repair Case" clears the session for your privacy.

🤝 Contributing
If you're a developer or tech interested in improving the diagnostic prompts or adding new data sources, feel free to open a Pull Request.
