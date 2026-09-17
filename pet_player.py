import sys
import os
import json
import random
from PySide6.QtCore import Qt, QTimer, QPoint, QRect, QSize, QUrl
from PySide6.QtGui import QPixmap, QPainter, QAction, QCursor
from PySide6.QtWidgets import QApplication, QWidget, QMenu, QLabel, QVBoxLayout

# Load pet configuration
class PetConfig:
    def __init__(self, config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.id = data["id"]
        self.display_name = data["displayName"]
        self.description = data["description"]
        
        self.config_dir = os.path.dirname(config_path)
        self.spritesheet_path = os.path.join(self.config_dir, data["spritesheetPath"])
        
        anim = data["animation"]
        self.columns = anim["columns"]
        self.rows = anim["rows"]
        self.cell_width = anim["cellWidth"]
        self.cell_height = anim["cellHeight"]
        self.states = anim["states"]

# Speech Bubble Widget
class SpeechBubble(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow | Qt.NoDropShadowWindowHint | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        self.layout = QVBoxLayout(self)
        self.label = QLabel(self)
        self.label.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 230);
                border: 2px solid #5a85c8;
                border-radius: 8px;
                padding: 6px;
                color: #2b3e50;
                font-family: "Microsoft YaHei", sans-serif;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        self.layout.addWidget(self.label)
        self.hide()
        
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)

    def show_text(self, text, pos, duration=3000):
        self.label.setText(text)
        self.adjustSize()
        # Position bubble centered above the pet
        self.move(pos.x() + (192 - self.width()) // 2, pos.y() - self.height() - 5)
        self.show()
        self.timer.start(duration)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.transparent)
        painter.end()

# Main Pet Window
class DesktopPet(QWidget):
    def __init__(self):
        # Frameless, Always on Top, Taskbar hide (Tool), Disable Shadows, and Disable Focus Grabbing
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoDropShadowWindowHint | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")
        
        # Resolve skin directory (支持 model 与 jiruxue_miaojiang)
        candidates = []
        if hasattr(sys, '_MEIPASS'):
            candidates.append(os.path.join(sys._MEIPASS, "dist", "model", "pet.json"))
            candidates.append(os.path.join(sys._MEIPASS, "model", "pet.json"))
            candidates.append(os.path.join(sys._MEIPASS, "dist", "jiruxue_miaojiang", "pet.json"))
            candidates.append(os.path.join(sys._MEIPASS, "jiruxue_miaojiang", "pet.json"))
        
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            candidates.append(os.path.join(exe_dir, "dist", "model", "pet.json"))
            candidates.append(os.path.join(exe_dir, "model", "pet.json"))
            candidates.append(os.path.join(exe_dir, "dist", "jiruxue_miaojiang", "pet.json"))
            candidates.append(os.path.join(exe_dir, "jiruxue_miaojiang", "pet.json"))

        curr_dir = os.path.abspath(os.path.dirname(__file__))
        candidates.append(os.path.join(curr_dir, "dist", "model", "pet.json"))
        candidates.append(os.path.join(curr_dir, "model", "pet.json"))
        candidates.append(os.path.join(curr_dir, "dist", "jiruxue_miaojiang", "pet.json"))
        candidates.append(os.path.join(curr_dir, "jiruxue_miaojiang", "pet.json"))

        skin_path = None
        for cand in candidates:
            if os.path.exists(cand):
                skin_path = cand
                break
        
        if not skin_path:
            skin_path = os.path.join(curr_dir, "dist", "model", "pet.json")

        self.config = PetConfig(skin_path)
        self.setWindowTitle("桌面宠物")
        self.setFixedSize(self.config.cell_width, self.config.cell_height)
        
        self.spritesheet = QPixmap(self.config.spritesheet_path)
        if self.spritesheet.isNull():
            print(f"Error: Failed to load spritesheet from {self.config.spritesheet_path}")
            sys.exit(1)
            
        # Pre-cache sprite frames for ultra-high performance and zero lag
        self.frames_cache = {}
        for state_name, state_info in self.config.states.items():
            row = state_info["row"]
            max_frames = state_info["frames"]
            self.frames_cache[state_name] = []
            for frame_idx in range(max_frames):
                src_x = frame_idx * self.config.cell_width
                src_y = row * self.config.cell_height
                frame_pixmap = self.spritesheet.copy(
                    src_x, src_y, 
                    self.config.cell_width, self.config.cell_height
                )
                self.frames_cache[state_name].append(frame_pixmap)
            
        self.current_state = "idle"
        self.frame_index = 0
        self.drag_position = QPoint()
        self.is_dragging = False
        
        # Movement boundaries (Screen Available Geometry)
        self.screen_geo = QApplication.primaryScreen().availableGeometry()
        self.floor_y = self.screen_geo.bottom() - self.config.cell_height
        
        # Position initially at bottom right
        self.move(self.screen_geo.right() - self.config.cell_width - 100, self.floor_y)
        
        # Main Character Display Label (optimizes rendering via hardware-accelerated C++ backing store)
        self.label = QLabel(self)
        self.label.setGeometry(0, 0, self.config.cell_width, self.config.cell_height)
        self.label.setAttribute(Qt.WA_TranslucentBackground, True)
        self.label.setStyleSheet("background: transparent;")
        self.label.setScaledContents(True)
        
        # Speech Bubble
        self.bubble = SpeechBubble()
        
        # Dialogues
        self.dialogues = [
            "大星，你在哪？",
            "我是幻音坊姬如雪。",
            "今天也要努力变强！",
            "不良人，各安天命。",
            "不要再戳我啦，好痒啊～",
            "你在写Bug吗？我帮你看着呢。",
            "星云……你一定要平安无事。"
        ]
        
        # Load external dialogues from 'dialogues.txt' next to the executable if present
        try:
            custom_path = os.path.join(exe_dir, "dialogues.txt")
            if os.path.exists(custom_path):
                with open(custom_path, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip()]
                if lines:
                    self.dialogues = lines
        except Exception as e:
            pass
        
        # Random Walk AI setup (15 seconds)
        self.walk_timer = QTimer(self)
        self.walk_timer.timeout.connect(self.walk_ai_tick)
        self.walk_timer.start(15000)
        
        self.walk_destination_x = self.x()
        self.walk_direction = 0  # -1: left, 1: right, 0: idle
        
        # Animation Frame update timer
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_animation_frame)
        self.anim_timer.start(150) # ~6-8 FPS
        
        # Physics (Gravity) timer
        self.physics_timer = QTimer(self)
        self.physics_timer.timeout.connect(self.apply_gravity)
        
        # Set initial frame pixmap
        initial_frames = self.frames_cache.get("idle")
        if initial_frames:
            self.label.setPixmap(initial_frames[0])
        self.show()  # Display the main pet window
        self.show_dialogue("喵呜~ 我是雪儿，陪你一起写代码吧！")

    def paintEvent(self, event):
        painter = QPainter(self)
        # CRITICAL FIX: Clear the translucent background before rendering.
        # This completely wipes previous frame data from the OS layered buffer,
        # preventing frame ghosting, duplicate stacking, and flashing.
        painter.fillRect(self.rect(), Qt.transparent)
        painter.end()

    def update_animation_frame(self):
        state_info = self.config.states.get(self.current_state, self.config.states["idle"])
        max_frames = state_info["frames"]
        self.frame_index = (self.frame_index + 1) % max_frames
        
        # Apply walking movement
        if self.current_state in ["running-left", "running-right"] and not self.is_dragging:
            step = 5
            if self.current_state == "running-left":
                new_x = self.x() - step
                if new_x < self.screen_geo.left():
                    new_x = self.screen_geo.left()
                    self.set_state("idle")
                self.move(new_x, self.y())
                if self.x() <= self.walk_destination_x:
                    self.set_state("idle")
            elif self.current_state == "running-right":
                new_x = self.x() + step
                if new_x > self.screen_geo.right() - self.config.cell_width:
                    new_x = self.screen_geo.right() - self.config.cell_width
                    self.set_state("idle")
                self.move(new_x, self.y())
                if self.x() >= self.walk_destination_x:
                    self.set_state("idle")
                    
        # Update pixmap on label
        frames = self.frames_cache.get(self.current_state)
        if frames:
            frame_pixmap = frames[self.frame_index % len(frames)]
            self.label.setPixmap(frame_pixmap)
            self.update() # Force repaint to trigger DWM alpha composition

    def set_state(self, state):
        if state in self.config.states:
            self.current_state = state
            self.frame_index = 0
            frames = self.frames_cache.get(self.current_state)
            if frames:
                self.label.setPixmap(frames[0])
                self.update()

    def sync_bubble_position(self):
        if self.bubble.isVisible():
            self.bubble.move(
                self.x() + (self.config.cell_width - self.bubble.width()) // 2, 
                self.y() - self.bubble.height() - 5
            )

    def moveEvent(self, event):
        super().moveEvent(event)
        self.sync_bubble_position()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.set_state("waving") # Play waving/dangling when clicked
            self.physics_timer.stop()
            self.walk_timer.stop()
            event.accept()

    def mouseMoveEvent(self, event):
        if Qt.LeftButton and self.is_dragging:
            old_pos = self.pos()
            new_pos = event.globalPosition().toPoint() - self.drag_position
            self.move(new_pos)
            
            # Determine drag direction
            if new_pos.x() < old_pos.x():
                self.set_state("running-left")
            elif new_pos.x() > old_pos.x():
                self.set_state("running-right")
            else:
                self.set_state("waving")
                
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = False
            event.accept()
            # Drop the pet -> start gravity ONLY if they are not already on the floor
            if self.y() < self.floor_y:
                self.set_state("jumping") # Falling animation
                self.physics_timer.start(15) # Fast tick for physics
            self.walk_timer.start(15000)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Trigger a random stationary cute animation and speech
            action = random.choice(["wave", "happy", "lying", "sad", "speak"])
            
            if action == "wave":
                self.set_state("waving")
                self.show_dialogue("你在叫我吗？给你打个招呼吧~")
                QTimer.singleShot(1500, lambda: self.set_state("idle"))
            elif action == "happy":
                self.set_state("running")
                self.show_dialogue("啦啦啦~ 好开心呀！")
                QTimer.singleShot(3000, lambda: self.set_state("idle"))
            elif action == "lying":
                self.set_state("waiting")
                self.show_dialogue("趴在这里好舒服哦~")
                QTimer.singleShot(5000, lambda: self.set_state("idle"))
            elif action == "sad":
                self.set_state("failed")
                self.show_dialogue("呜呜呜……不要欺负我嘛……")
                QTimer.singleShot(3000, lambda: self.set_state("idle"))
            elif action == "speak":
                self.speak_random()
                
            event.accept()

    def apply_gravity(self):
        fall_speed = 10
        new_y = self.y() + fall_speed
        if new_y >= self.floor_y:
            new_y = self.floor_y
            self.move(self.x(), new_y)
            self.physics_timer.stop()
            # Dizzy/fallen reaction when landing
            self.set_state("failed")
            QTimer.singleShot(1000, lambda: self.set_state("idle"))
        else:
            self.move(self.x(), new_y)

    def force_walk(self):
        if self.is_dragging or self.physics_timer.isActive():
            return
            
        # Reset walk timer interval
        self.walk_timer.start(15000)
        
        # Decide direction based on boundaries to avoid running off-screen
        margin = 150
        direction = random.choice(["left", "right"])
        if self.x() < self.screen_geo.left() + margin:
            direction = "right"
        elif self.x() > self.screen_geo.right() - self.config.cell_width - margin:
            direction = "left"
            
        distance = random.randint(150, 400)
        if direction == "left":
            self.walk_destination_x = max(self.screen_geo.left(), self.x() - distance)
            if self.walk_destination_x < self.x():
                self.set_state("running-left")
                self.show_dialogue("好啦，这就跑给你看！")
        else:
            self.walk_destination_x = min(self.screen_geo.right() - self.config.cell_width, self.x() + distance)
            if self.walk_destination_x > self.x():
                self.set_state("running-right")
                self.show_dialogue("这就出发跑起来！")

    def walk_ai_tick(self):
        if self.is_dragging or self.physics_timer.isActive():
            return
            
        action = random.choice(["idle", "walk_left", "walk_right", "wave", "speak", "happy", "lying", "sad"])
        
        if action == "idle":
            self.set_state("idle")
        elif action == "walk_left":
            distance = random.randint(100, 300)
            self.walk_destination_x = max(self.screen_geo.left(), self.x() - distance)
            if self.walk_destination_x < self.x():
                self.set_state("running-left")
        elif action == "walk_right":
            distance = random.randint(100, 300)
            self.walk_destination_x = min(self.screen_geo.right() - self.config.cell_width, self.x() + distance)
            if self.walk_destination_x > self.x():
                self.set_state("running-right")
        elif action == "wave":
            self.set_state("waving")
            QTimer.singleShot(1500, lambda: self.set_state("idle"))
        elif action == "happy":
            self.set_state("running")  # Happy jump loop
            QTimer.singleShot(3000, lambda: self.set_state("idle"))
        elif action == "lying":
            self.set_state("waiting")  # Lying down (hands supporting face)
            QTimer.singleShot(5000, lambda: self.set_state("idle"))
        elif action == "sad":
            self.set_state("failed")   # Sad/failed state
            QTimer.singleShot(3000, lambda: self.set_state("idle"))
        elif action == "speak":
            self.speak_random()

    def speak_random(self):
        if not self.dialogues:
            return
        idx = random.randint(0, len(self.dialogues) - 1)
        dialogue = self.dialogues[idx]
        self.show_dialogue(dialogue)
        # Play a random cute expression while speaking
        expressive_state = random.choice(["waving", "running", "waiting", "idle"])
        if expressive_state in self.config.states:
            self.set_state(expressive_state)
            QTimer.singleShot(3000, lambda: self.set_state("idle"))

    def show_dialogue(self, text):
        self.bubble.show_text(text, self.pos())

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #CCCCCC;
                font-family: "Microsoft YaHei", sans-serif;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 20px;
            }
            QMenu::item:selected {
                background-color: #5a85c8;
                color: white;
            }
        """)
        
        action_wave = QAction("打个招呼", self)
        action_wave.triggered.connect(lambda: [self.set_state("waving"), QTimer.singleShot(1500, lambda: self.set_state("idle"))])
        menu.addAction(action_wave)
        
        action_talk = QAction("跟我说话", self)
        action_talk.triggered.connect(lambda: self.speak_random())
        menu.addAction(action_talk)
        
        action_walk = QAction("让它乱跑", self)
        action_walk.triggered.connect(self.force_walk)
        menu.addAction(action_walk)
        
        menu.addSeparator()
        
        action_quit = QAction("退出", self)
        action_quit.triggered.connect(self.close_all)
        menu.addAction(action_quit)
        
        menu.exec(event.globalPos())

    def close_all(self):
        self.bubble.close()
        self.close()
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = DesktopPet()
    sys.exit(app.exec())
