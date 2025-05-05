import time
import math
import random
import arcade
import pymunk
from arcade import (
    check_for_collision_with_list,
)

TILE_SCALING = 2


WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Sprite Tiled Map Example"
SPRITE_PIXEL_SIZE = 128
# GRID_PIXEL_SIZE = SPRITE_PIXEL_SIZE * TILE_SCALING
GRID_PIXEL_SIZE = 32 * TILE_SCALING
CAMERA_PAN_SPEED = 0.30

# Physics
MOVEMENT_SPEED = 10
PLAYER_MOVE_FORCE = 4000
JUMP_SPEED = 20
PLAYER_JUMP_IMPULSE = 1800
GRAVITY = 2000
MAX_SPEED = 50
SHOOT_COOLDOWN = 60
BULLET_SPEED = 10

# Damping - Amount of speed lost per second
DEFAULT_DAMPING = 1.0
PLAYER_DAMPING = .8   

# Friction between objects
PLAYER_FRICTION = 1.0
WALL_FRICTION = 0.7
DYNAMIC_ITEM_FRICTION = 0.6

# Mass (defaults to 1)
PLAYER_MASS = 2.0

# Keep player from going too fast
PLAYER_MAX_HORIZONTAL_SPEED = 450
PLAYER_MAX_VERTICAL_SPEED = 1000

DRONE_SALING=1
#PLAYER ANIMATION CONSTANTS
PLAYER_SCALING = 1
DEAD_ZONE = 0.1
RIGHT_FACING = 0 # Constants used to track if the player is facing left or right
LEFT_FACING = 1
DISTANCE_TO_CHANGE_TEXTURE = 20 # How many pixels to move before we change the texture in the walking animation

class GameView(arcade.View):
    """Main application class."""

    def __init__(self):
        super().__init__()
        self.left_pressed: bool = False
        self.right_pressed: bool = False
        self.down_pressed: bool = False
        self.up_pressed: bool = False
        self.left_mouse_pressed: bool = False
        self.right_mouse_pressed: bool = False
    
        self.player_list = None
        self.objects_list = None
        self.balls_list = None
        self.magnets_list = None

        # Tilemap Object
        self.tile_map = None

        # Sprite lists
        self.enemy_list = None
        self.wall_list = None
        self.coin_list = None

        self.player_bullet_list = None
        self.enemy_bullet_list = None
        self.shoot_cooldown = SHOOT_COOLDOWN

        # Variables
        self.left_mouse_pressed_for: int = 0
        self.right_mouse_pressed_for: int = 0

        self.physics_engine = None
        self.end_of_map = 0
        self.game_over = False
        self.last_time = None
        self.frame_count = 0

        # Cameras
        self.camera = None
        self.camera_new_position = None
        self.camera_bounds = None
        self.gui_camera = None

    def setup(self):
        """Set up the game and initialize the variables."""

        # Sprite lists
        self.player_list = arcade.SpriteList()

        self.objects_list = arcade.SpriteList()
        self.balls_list = arcade.SpriteList()
        self.magnets_list = arcade.SpriteList()
        
        # Set up the enemies
        self.enemy_list = arcade.SpriteList()
        self.enemy_bullet_list = arcade.SpriteList()

        # Choose a map from files
        map_name = "Maps/karte.tmx"

        layer_options = {
            "Platforms": {"use_spatial_hash": True},
            "Coins": {"use_spatial_hash": True},
        }

        # Read in the tiled map
        self.tile_map = arcade.load_tilemap(
            map_name, layer_options=layer_options, scaling=TILE_SCALING
        )
        self.end_of_map = self.tile_map.width * GRID_PIXEL_SIZE

        # Set wall and coin SpriteLists
        self.wall_list = self.tile_map.sprite_lists["Platforms"]
        self.coin_list = self.tile_map.sprite_lists["Coins"]

        # --- Other stuff
        # Set the background color
        # self.window.background_color = arcade.color.Color(10, 50, 30)

        # Keep player from running through the wall_list layer
        walls = [self.wall_list, ]
        self.gravity_constant = GRAVITY
        # Create a physics engine
        self.physics_engine = arcade.PymunkPhysicsEngine(
            damping=DEFAULT_DAMPING,
            gravity=(0, -self.gravity_constant),
            maximum_incline_on_ground=1
            )
        # Add walls to the engine
        self.physics_engine.add_sprite_list(
            self.wall_list,
            friction=WALL_FRICTION,
            collision_type="wall",
            body_type=arcade.PymunkPhysicsEngine.STATIC,
            elasticity=0.25
            )

        self.camera = arcade.Camera2D()
        self.gui_camera = arcade.Camera2D()

        # Use the tilemap to limit the camera's position
        max_x = self.end_of_map - self.window.width / 2.0
        # max_y = WINDOW_HEIGHT - self.window.height / 2.0
        max_y = self.tile_map.height * GRID_PIXEL_SIZE - self.window.height / 2.0
        self.camera_bounds = arcade.LRBT(
            self.window.width / 2.0, max_x,
            self.window.height / 2.0, max_y
        )

        self.camera_new_position = (WINDOW_WIDTH / 2, WINDOW_HEIGHT * 2)
        
        # Center camera on user
        self.pan_camera_to_user()
        
        # Text
        self.fps_text = arcade.Text(
            "FPS:  60",
            x=20,
            y=WINDOW_HEIGHT - 40,
            color=arcade.color.BLACK,
            font_size=14
        )
        self.distance_text = arcade.Text(
            "0.0",
            x=10,
            y=20,
            color=arcade.color.BLACK,
            font_size=14,
        )

        self.bg_color=(100, 200, 225)

        self.game_over = False

    def on_draw(self):
        """
        Render the screen.
        """
        arcade.set_background_color(self.bg_color)
        # This command has to happen before we start drawing
        self.camera.use()
        self.clear()

        # Start counting frames
        self.frame_count += 1

        # Draw all the sprites.
        self.objects_list.draw()
        self.balls_list.draw()
        self.magnets_list.draw()
        self.enemy_list.draw()
        self.wall_list.draw()
        self.coin_list.draw()
        
        # Activate GUI camera for FPS, distance and hit boxes
        # This will adjust text position based on viewport
        self.gui_camera.use()

        # Calculate FPS if conditions are met
        if self.last_time and self.frame_count % 60 == 0:
            fps = round(1.0 / (time.time() - self.last_time) * 60)
            self.fps_text.text = f"FPS: {fps:3d}"

        # Draw FPS text
        self.fps_text.draw()

        # Get time for every 60 frames
        if self.frame_count % 60 == 0:
            self.last_time = time.time()

        # Enable to draw hit boxes
        # self.wall_list.draw_hit_boxes()
        # self.wall_list_objects.draw_hit_boxes()

        # Draw game over text if condition met
        if self.game_over:
            arcade.draw_text(
                "Game Over",
                200,
                200,
                arcade.color.BLACK,
                40,
            )

    def on_key_press(self, key, modifiers):
        """
        Called whenever a key is pressed.
        """
        if key == arcade.key.LEFT or key == arcade.key.A:
            self.left_pressed = True
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.right_pressed = True
        if key == arcade.key.UP or key == arcade.key.W:
            self.up_pressed = True
        elif key == arcade.key.DOWN or key == arcade.key.S:
            self.down_pressed = True
        if key == arcade.key.R:
            self.setup()
            
    def on_key_release(self, key, modifiers):
        """
        Called when the user releases a key.
        """
        if key == arcade.key.LEFT or key == arcade.key.A:
            self.left_pressed = False
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.right_pressed = False
        if key == arcade.key.UP or key == arcade.key.W:
            self.up_pressed = False
        elif key == arcade.key.DOWN or key == arcade.key.S:
            self.down_pressed = False

    def on_mouse_press(self, x, y, button, key_modifiers):
        """
        Called when the user presses a mouse button.
        """
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.left_mouse_pressed = True
            self.left_mouse_pressed_for = 5
        elif button == arcade.MOUSE_BUTTON_RIGHT:
            self.right_mouse_pressed = True
            self.right_mouse_pressed_for = 5

    def on_mouse_release(self, x, y, button, modifiers):
        """
        Called when the user releases a mouse button.
        """
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.left_mouse_pressed = False
            x += self.camera.position.x - WINDOW_WIDTH / 2
            y += self.camera.position.y - WINDOW_HEIGHT / 2
            self.spawn_circle(x, y, self.left_mouse_pressed_for)
        elif button == arcade.MOUSE_BUTTON_RIGHT:
            self.right_mouse_pressed = False
            x += self.camera.position.x - WINDOW_WIDTH / 2
            y += self.camera.position.y - WINDOW_HEIGHT / 2
            self.spawn_magnet(x, y, self.right_mouse_pressed_for)


    def on_update(self, delta_time):
        """Movement and game logic"""

        # Call update on all sprites
        if not self.game_over:
            self.physics_engine.step()
            self.enemy_list.update()
            self.enemy_bullet_list.update()

        # Moving the camera
        if self.left_pressed:
            self.camera_new_position = (self.camera.position[0] - 100, self.camera.position[1])
        elif self.right_pressed:
            self.camera_new_position = (self.camera.position[0] + 100, self.camera.position[1])
        if self.up_pressed:
            self.camera_new_position = (self.camera.position[0], self.camera.position[1] + 100)
        elif self.down_pressed:
            self.camera_new_position = (self.camera.position[0], self.camera.position[1] - 100)

        # Magnetics mechanik
        for magnet in self.magnets_list:
            for ball in self.balls_list:
                dx = magnet.position[0]-ball.position[0]
                dy = magnet.position[1]-ball.position[1]
                if True:
                    self.physics_engine.apply_force(magnet, [-100*magnet.strength/(dx**2), -100*magnet.strength/(dy**2)])
                    self.physics_engine.apply_force(ball, [10000*magnet.strength/(dx**2), 10000*magnet.strength/(dy**2)])
                    print(f"{dx},  {dy}")
                    print(f"{magnet.strength},  {10000*magnet.strength/(dy**2)}")
        # Clearing onjects
        for object in self.balls_list:
            if object.right < 0 or object.left > self.end_of_map or object.top < 0:
                object.remove_from_sprite_lists()
        for object in self.magnets_list:
            if object.right < 0 or object.left > self.end_of_map or object.top < 0:
                object.remove_from_sprite_lists()

        # Player holds mouse
        if self.left_mouse_pressed and self.left_mouse_pressed_for <= 50:
            self.left_mouse_pressed_for += 1
        if self.right_mouse_pressed and self.right_mouse_pressed_for <= 50:
            self.right_mouse_pressed_for += 1

        # Pan to the user
        self.pan_camera_to_user(CAMERA_PAN_SPEED)

    def pan_camera_to_user(self, panning_fraction: float = 1.0):
        """ Manage Scrolling """
        self.camera.position = arcade.math.smerp_2d(
            self.camera.position,
            self.camera_new_position,
            self.window.delta_time,
            panning_fraction,
        )

        self.camera.position = arcade.camera.grips.constrain_xy(
            self.camera.view_data,
            self.camera_bounds
        )
    
    def spawn_circle(self, x: int, y: int, radius: int):
        body = arcade.SpriteCircle(
            radius=radius,
            color=(random.randint(50,255), random.randint(50,255), random.randint(0,155)),
        )
        body.position = (x, y)
        self.balls_list.append(body)
        self.physics_engine.add_sprite(
            body,
            mass=radius*radius/250,
            friction=0.75,
            elasticity=0.75,
            damping=1,
            max_horizontal_velocity=PLAYER_MAX_HORIZONTAL_SPEED,
            max_vertical_velocity=PLAYER_MAX_VERTICAL_SPEED
        )

    def spawn_magnet(self, x: int, y: int, strength: int):
        body = arcade.Sprite(
            "Assets\Sprite\magnet.png",
            scale=PLAYER_SCALING / 2,
            center_x=x,
            center_y=y,
        )
        setattr(body, "strength", strength)
        self.magnets_list.append(body)
        self.physics_engine.add_sprite(
            body,
            mass=20,
            friction=0.75,
            elasticity=0.25,
            damping=1,
            max_horizontal_velocity=PLAYER_MAX_HORIZONTAL_SPEED,
            max_vertical_velocity=PLAYER_MAX_VERTICAL_SPEED
        )

class Bullet(arcade.Sprite):
    """ Bullets that players and emenies can shoot """
    def __init__(self, x, y, angle, speed=BULLET_SPEED):
        super().__init__(":resources:images/space_shooter/laserRed01.png", scale=0.8)
        self.center_x = x
        self.center_y = y
        self.change_y = speed * math.cos(angle)
        self.change_x = speed * math.sin(angle)
        self.angle = math.degrees(angle)

def main():
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    game = GameView()
    game.setup()

    window.show_view(game)
    window.run()


if __name__ == "__main__":
    main()
