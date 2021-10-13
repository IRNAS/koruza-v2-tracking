import matplotlib.pyplot as plt

IMG_FOLDER = "/home/pi/koruza_v2/koruza_v2_tracking/images/"
z_min = -40
z_max = 2

class Heatmap():
    # a move of 1000 is roughly 18 pixels wide and high (round up)  TODO get exact number
    def __init__(self, offset_x, offset_y):
        """Heatmap class"""
        self.pos_x = []
        self.pos_y = []
        self.rx_pow = []

        self.x_ratio = 1000 / 18
        self.y_ratio = 1000 / 18

        self.offset_x = offset_x
        self.offset_y = offset_y

    def add_point(self, pos_x, pos_y, rx_dBm):
        """Append new point to heatmap array"""
        self.pos_x.append(pos_x)
        self.pos_y.append(pos_y)
        self.rx_pow.append(rx_dBm)

    def find_max_of_heatmap(self):
        """Get pos_x and pos_y of heatmap"""
        max_rx_pow = -100
        selected_index = 0
        for index, rx_pow in enumerate(self.rx_pow):
            if rx_pow > max_rx_pow:
                selected_index = index

        print(f"Selected index: {selected_index}")
        return self.pos_x[selected_index], self.pos_y[selected_index], self.rx_pow[selected_index]  # return selected point

    def clear_heatmap(self):
        """Clear entire heatmap"""
        self.pos_x = []
        self.pos_y = []
        self.rx_pow = []

    def save_image(self, filename, size):
        """Generate and save image from heatmap data"""
        fig, ax = plt.subplots()
        x = [self.offset_x + motor_x / self.x_ratio for motor_x in self.pos_x]
        y = [self.offset_y + motor_y / self.y_ratio for motor_y in self.pos_y]
        ax.scatter(x, y, c=self.rx_pow[:len(x)], s=1, vmin=z_min, vmax=z_max)    
        # ax.grid(True)
        fig.tight_layout()
        plt.xlim([0, 720])
        plt.ylim([0, 720])
        plt.savefig(IMG_FOLDER + filename, dpi=500)

    def save_heatmap_data(self, filename):
        """Save array to text file"""
        with open(IMG_FOLDER + filename, "w") as file:
            file.write(f"offset_x: {self.offset_x}, offset_y: {self.offset_y}\n")
            for point in zip(self.pos_x, self.pos_y, self.rx_pow):
                file.write(f"{point[0]}, {point[1]}, {point[2]}\n")