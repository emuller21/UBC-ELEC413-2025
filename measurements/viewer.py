'''
by Lukas Chrostowski, 2025
written with the help of ChatGPT 4.o
'''

import os
import re
import requests
import zipfile
import shutil
import pathlib
import klayout.db as pya
import siepicfab_ebeam_zep
import SiEPIC
from SiEPIC.utils import find_automated_measurement_labels
import matplotlib.pyplot as plt
import scipy.io
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLabel, QTabWidget, QScrollArea, QPushButton, QTextEdit
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar

CONST_NoiseFloor = -50  # only plot files that exceed the measurement noise floor

'''
matches example:
['/Users/lukasc/Documents/GitHub/openEBL-2024-10/measurements/mat_files/Lukas_data_2024T3/LukasChrostowski_MZI1/09-Nov-2024 06.05.22.mat', {'opt_in': 'opt_in_TE_1550_device_LukasChrostowski_MZI1', 'x': 673, 'y': 4322, 'pol': 'TE', 'wavelength': '1550', 'type': 'device', 'deviceID': 'LukasChrostowski', 'params': ['MZI1'], 'Text': ('opt_in_TE_1550_device_LukasChrostowski_MZI1',r0 673000,4322000)}]
'''

class TabbedGUI(QMainWindow):
    def __init__(self, layout, matches):
        super().__init__()
        self.setWindowTitle("SiEPIC openEBL data viewer")
        self.setGeometry(100, 100, 800, 600)
        self.matches = dict(sorted(matches.items()))
        self.layout = layout
        self.top_cell = layout.top_cell()
        self.legend_enabled = True  # Track legend state
        self.multi_selection = False  # Track selection mode
        
        self.initUI()

    def initUI(self):
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        
        # List Widget on the Left
        left_layout = QVBoxLayout()
        self.listWidget = QListWidget()
        #self.listWidget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.listWidget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        for item in sorted(self.matches.keys(), key=str.casefold):
            self.listWidget.addItem(item)
        self.listWidget.itemSelectionChanged.connect(self.update_tabs)

        # Add selection mode toggle button
        self.selection_button = QPushButton("Selection: Single")
        self.selection_button.clicked.connect(self.toggle_selection_mode)
        left_layout.addWidget(self.listWidget)
        left_layout.addWidget(self.selection_button)
        main_layout.addLayout(left_layout, 1)  # Takes 1 part of the space
        
        # Tabs on the Right
        self.tabs = QTabWidget()
        
        # Tab 2: Image
        self.tab2 = QWidget()
        self.scrollArea = QScrollArea()
        self.imageLabel = QLabel("Select an item to display an image")
        self.imageLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scrollArea.setWidget(self.imageLabel)
        self.scrollArea.setWidgetResizable(True)
        layout2 = QVBoxLayout()
        layout2.addWidget(self.scrollArea)
        self.tab2.setLayout(layout2)
        self.display_klayout_cell_image(self.layout.top_cell().name, self.layout.top_cell()) #, width=self.scrollArea.width()*0.99)
        
        # Tab 3: Data Plot
        self.tab3 = QWidget()
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.legend_button = QPushButton("Toggle Legend")
        self.legend_button.clicked.connect(self.toggle_legend)
        layout3 = QVBoxLayout()
        layout3.addWidget(self.toolbar)
        layout3.addWidget(self.canvas)
        layout3.addWidget(self.legend_button)
        self.tab3.setLayout(layout3)
        
        # Tab 4: Netlist
        self.tab4 = QWidget()
        self.text_output = QTextEdit()
        self.text_output.setReadOnly(True)
        layout4 = QVBoxLayout()
        layout4.addWidget(self.text_output)
        self.tab4.setLayout(layout4)
        
        # Add tabs to the main layout
        self.tabs.addTab(self.tab2, "Image")
        self.tabs.addTab(self.tab3, "Plot")
        self.tabs.addTab(self.tab4, "Netlist")
        main_layout.addWidget(self.tabs, 3)  # Takes 3 parts of the space
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def toggle_selection_mode(self):
        """
        Toggles between Single and Multi selection mode.
        """
        self.multi_selection = not self.multi_selection
        mode = QListWidget.SelectionMode.MultiSelection if self.multi_selection else QListWidget.SelectionMode.SingleSelection
        self.listWidget.setSelectionMode(mode)
        self.selection_button.setText("Selection: Multi" if self.multi_selection else "Selection: Single")

    def resizeEvent(self, event):
        """
        Resize event to dynamically adjust image size.
        """
        if self.imageLabel.pixmap():
            self.display_klayout_cell_image(width=self.scrollArea.width()*0.99)
        super().resizeEvent(event)

    def update_tabs(self):
        selected_items = [item.text() for item in self.listWidget.selectedItems()]
        if not selected_items:
            self.ax.clear()
            #print(self.layout.top_cell().name)
            self.display_klayout_cell_image(self.layout.top_cell().name, self.layout.top_cell(), width=self.scrollArea.width()*0.99)
            self.canvas.draw()
            return
        
        self.ax.clear()
        for selected_key in selected_items:
            if selected_key in self.matches:
                mat_file_path = self.matches[selected_key][0]  # Get the first associated file
                self.plot_mat_data(mat_file_path, selected_key, len(selected_items)>1)
                self.display_klayout_cell_image(selected_key, width=self.scrollArea.width()*0.99)
                opt_in_selection_text=[self.matches[selected_key][1]['opt_in']]
                print(opt_in_selection_text)
                try:
                    text_subckt, text_main, *_ = self.cell.spice_netlist_export(opt_in_selection_text=opt_in_selection_text)
#                    print(text_subckt, text_main)
                    self.text_output.setPlainText(text_subckt)
                    self.text_output.append(text_main)
                except:
                    text = 'No netlist available for this circuit.'
                    self.text_output.setPlainText(text)
                    pass
        
        if len(selected_items)>1:
            self.ax.set_title(f"Spectrum Data for selected files")
        if self.legend_enabled:
            self.ax.legend()
        self.canvas.draw()

    def toggle_legend(self):
        """
        Toggles the visibility of the legend.
        """
        self.legend_enabled = not self.legend_enabled
        self.update_tabs()
    
    def plot_mat_data(self, mat_file_path, title, multi=False):
        """
        Reads and plots the spectrum data from a .mat file.
        """
        mat_data = scipy.io.loadmat(mat_file_path)
        test_result = mat_data.get("testResult")
        test_result_inner = test_result[0, 0]
        rows_data = test_result_inner["rows"]
        rows_inner = rows_data[0, 0]
        wavelengths = test_result[0][0][0]['wavelength'].flatten()[0]
        
        for i in range(1, 5):
            channel_key = f"channel_{i}"
            if channel_key in rows_inner.dtype.names:
                spectrum_data = rows_inner[channel_key].flatten()
                if max(spectrum_data) > CONST_NoiseFloor:
                    if multi:
                        self.ax.plot(wavelengths, spectrum_data, label=f"{title}:{i}")
                    else:
                        self.ax.plot(wavelengths, spectrum_data, label=f"channel:{i}")
        
        self.ax.set_xlabel("Wavelength [nm]")
        self.ax.set_ylabel("Transmission [dB]")
        self.ax.set_title(f"Spectrum Data for {title}")
        self.ax.grid(True)

    def display_klayout_cell_image(self, cell_name=None, cell=None, width=400):
        """
        Generates an image of the KLayout cell and displays it in Tab 2.
        """
        layer_optin = [10,0]
        layout = self.layout
        if cell_name:
            self.cell_name = cell_name
        if not cell_name:
            if 'cell_name' in dir(self):
                cell_name = self.cell_name
        for m in self.matches:
            if cell_name == m:
                cell = find_text_label(layout, layer_optin, self.matches[m][1]['opt_in'])
#                print(f"is cell const object? 2 {cell._is_const_object()}")
                break
        if cell:
            # draw an arrow
            # find opt_in position:
            iter = cell.begin_shapes_rec(layout.layer(layer_optin))
            trans = None
            while not (iter.at_end()):
                if iter.shape().is_text():
                    text = iter.shape().text
                    if self.matches[m][1]['opt_in'] == text.string:
                        trans = pya.Trans(text.x, text.y)
                iter.next()
            if trans:
                arrow_shape = draw_right_facing_arrow(cell, layer_optin, trans)
            else:
                print('opt_in label location not found.')
                arrow_shape = draw_right_facing_arrow(cell, layer_optin)
            # image_path = os.path.join(path,f"{cell_name}.png")
            image_path = os.path.join(SiEPIC._globals.TEMP_FOLDER, f"{cell_name}.png")
            im = cell.image(image_path, width=width, retina=False)
            qp = QPixmap(image_path)
            self.imageLabel.setPixmap(qp)
            #self.imageLabel.setPixmap(QPixmap(image_path).scaled(400, 300, Qt.AspectRatioMode.KeepAspectRatio))
            # arrow_shape.erase()
            cell.shapes(layout.layer(layer_optin)).erase(arrow_shape)
            self.cell = cell
        else:
            self.imageLabel.setText("Cell not found in layout")
            self.cell = None
        return None

def draw_right_facing_arrow(cell, layer, trans=pya.Trans()):
    """
    Draws a right-facing arrow, with a transformed location
    
    Args:
        cell (pya.Cell): The cell in which the arrow will be drawn.
        layer: e.g., [10,0]
        trans: pya.Trans transformation
        
    """
    # Define the layer
    layer_index = cell.layout().layer(layer)

    # Define the arrow points
    length = 60e3  # microns
    width = 20e3   # microns
    
    points = [
        pya.Point(-length, width // 2),       # Left upper corner
        pya.Point(-length * 0.4, width // 2), # Arrow cut upper
        pya.Point(-length * 0.4, width),      # Right upper end
        pya.Point(0, 0),                      # Right middle
        pya.Point(-length * 0.4, -width),     # Right lower end
        pya.Point(-length * 0.4, -width // 2),# Arrow cut lower
        pya.Point(-length, -width // 2),      # Left lower corner
    ]

    # Create the polygon and insert it into the layout
    polygon = pya.Polygon(points)
    # this should work:
    # cell.shapes(layer_index).insert(polygon)
    # but returns an error: RuntimeError: Cannot call non-const method on a const reference in Shapes.insert
    # KLayout bug? https://github.com/KLayout/klayout/issues/235
    # work around:
    # arrow_shape = cell.layout().cell(cell.cell_index()).shapes(layer_index).insert(polygon.transformed(trans))
    # solved at the original cell object creation
    arrow_shape = cell.shapes(layer_index).insert(polygon.transformed(trans))
    return arrow_shape

'''
# Example usage
layout = pya.Layout()
top_cell = layout.create_cell("Top")
draw_right_facing_arrow(top_cell, [10,0])
layout.write("left_arrow.gds")
'''

def disable_libraries():
    print('Disabling KLayout libraries')
    for l in pya.Library().library_ids():
        print(' - %s' % pya.Library().library_by_id(l).name())
        pya.Library().library_by_id(l).delete()
    
def load_layout_and_extract_labels():
    """
    Loads the layout file located at ../aggregate/Shuksan.oas and extracts opt_in labels using SiEPIC.
    
    Returns:
        list: Extracted opt_in labels from the layout.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    layout_path = os.path.abspath(os.path.join(script_dir, '..', 'aggregate', 'Shuksan.oas'))
    
    if not os.path.exists(layout_path):
        raise FileNotFoundError(f"Layout file not found at expected location: {layout_path}")
    
    # Load all the layouts, without the libraries (no PCells)
    disable_libraries()

    layout = pya.Layout()
    layout.read(layout_path)
    layout.technology_name = "SiEPICfab_EBeam_ZEP"
    
    top_cell = layout.top_cell()
    if not top_cell:
        raise RuntimeError("No top cell found in the layout.")
    
    labels = find_automated_measurement_labels(top_cell)
    print(f"Extracted number of labels: {len(labels[1])}")
    return layout, labels


def match_files_with_labels(mat_files_dir, labels):
    """
    Matches .mat files in the mat_files directory with the extracted opt_in labels.
    
    Args:
        mat_files_dir (str): The directory containing .mat files.
        labels (list): Extracted opt_in labels from the layout.
    
    Returns:
        dict: A mapping of labels to matching .mat files.
    """
    matches = {}
    for root, _, files in os.walk(mat_files_dir):
        for label in labels[1]:
            device_id = label.get('deviceID', '')
            params = "_".join(label.get('params', []))
            expected_folder_start = f"{device_id}_{params}".strip('_')

            if os.path.basename(root).startswith(expected_folder_start):
                for file in files:
                    if file.endswith(".mat"):
                        matches.setdefault(expected_folder_start, []).append(os.path.join(root, file))
                        matches[expected_folder_start].append(label)
    
    print(f"Matched files: {len(matches)}")
    return matches

def analyze_mat_file(mat_file_path, opt_in_name=''):
    """
    Analyzes the spectrum data from a .mat file and plots it.
    
    Args:
        mat_file_path (str): Path to the .mat file.
    """
    mat_data = scipy.io.loadmat(mat_file_path)
    test_result = mat_data.get("testResult")
    test_result_inner = test_result[0, 0]
    rows_data = test_result_inner["rows"]
    rows_inner = rows_data[0, 0]
    wavelengths = test_result[0][0][0]['wavelength'].flatten()[0]

    plt.figure(figsize=(12, 6))
    for i in range(1, 5):
        channel_key = f"channel_{i}"
        if channel_key in rows_inner.dtype.names:
            spectrum_data = rows_inner[channel_key].flatten()
            plt.plot(wavelengths, spectrum_data, label=f"{channel_key}")
    
    plt.xlabel("Wavelength [nm]")
    plt.ylabel("Transmission [dB]")
    plt.title(f"Spectrum Data for {opt_in_name}")
    plt.legend()
    plt.grid(True)
    plt.show()


def find_text_label(layout, layer_name, target_text):
    """
    Scans a layout file to find a specific text label on a given layer and returns the cell containing that text.
    
    Args:
        layout (pya.Layout): The layout object.
        layer_name (str): The layer name where the text is expected.
        target_text (str): The text label to find.
    
    Returns:
        pya.Cell: The cell containing the text, or None if not found.
    """
    layer_index = layout.layer(layer_name)
    if layer_index is None:
        raise Exception('Layer not found')
    
    iter = layout.top_cell().begin_shapes_rec(layer_index)
    while not iter.at_end():
        if iter.shape().is_text():
            text = iter.shape().text.string
            if text == target_text:
                # Ensure we return a non-Const cell, see issue: https://github.com/KLayout/klayout/issues/235
                # return layout.cell(iter.cell().name) 
                return layout.cell(iter.cell_index())
        iter.next()
    return None


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if 0:
        try:
            url = extract_measurement_url()
            print(f"Extracted URL: {url}")
        except Exception as e:
            print(f"Error: {e}")

    if 0:        
        try:
            url = "https://stratus.ece.ubc.ca/s/kfHwqfkcxNEMgXs/download"  # Test URL
            print(f"Using test URL: {url}")
            download_path = os.path.join(script_dir,'downloaded')
            filename = download_file(url, output_dir=download_path)
            mat_path = os.path.join(script_dir,'mat_files')
            unzip_and_copy_mat_files(filename, download_path, mat_path)
            # unzip_and_clean(filename, "downloaded_files")
        except Exception as e:
            print(f"Error: {e}")

    if 1:
        layout, labels = load_layout_and_extract_labels()
        mat_path = os.path.join(script_dir,'mat_files')
        matches = match_files_with_labels(mat_path, labels)
        '''
        for m in matches:
            if 'MZI1' in m:
                print(matches[m])
                #analyze_mat_file(matches[m][0],m)
        '''     
        app = QApplication(sys.argv)
        window = TabbedGUI(layout, matches)
        window.show()
        sys.exit(app.exec())

    if 0:
        layout, labels = load_layout_and_extract_labels()
        mat_path = os.path.join(script_dir,'mat_files')
        matches = match_files_with_labels(mat_path, labels)
        for m in matches:
            if 'MZI1' in m:
                print(matches[m])
                #analyze_mat_file(matches[m][0],m)
                
                cell = find_text_label(layout, [10,0], matches[m][1]['opt_in'])
                print(cell)
