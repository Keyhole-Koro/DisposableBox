from PIL import Image
import numpy as np

def create_spinner():
    # Create a simple spinning line animation
    frames = []
    size = 64
    center = size // 2
    length = size // 3
    
    for angle in range(0, 360, 30):
        frame = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        rad = np.radians(angle)
        x = center + length * np.cos(rad)
        y = center + length * np.sin(rad)
        
        # Draw line
        img = Image.fromarray(np.uint8(np.zeros((size, size, 4))))
        frames.append(frame)
    
    # Save as GIF
    frames[0].save(
        'loading_spinner.gif',
        save_all=True,
        append_images=frames[1:],
        duration=100,
        loop=0
    )

if __name__ == "__main__":
    create_spinner() 