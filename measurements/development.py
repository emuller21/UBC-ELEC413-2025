
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
from SiEPIC.scripts import connect_pins_with_waveguide, connect_cell, zoom_out, export_layout

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
                return layout.cell(iter.cell().name) 
        iter.next()
    return None

def disable_libraries():
    print('Disabling KLayout libraries')
    for l in pya.Library().library_ids():
        print(' - %s' % pya.Library().library_by_id(l).name())
        pya.Library().library_by_id(l).delete()
    
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

    
if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))

    if 1:
        # Copy the layout for a circuit connected to an opt_in label
        layout, labels = load_layout_and_extract_labels()
        mat_path = os.path.join(script_dir,'mat_files')
        matches = match_files_with_labels(mat_path, labels)
        for m in matches:
            if 'MZI1' in m:
                print(matches[m])
                #analyze_mat_file(matches[m][0],m)
                
                cell = find_text_label(layout, [10,0], matches[m][1]['opt_in'])
                print(cell)
                
                
                # get the netlist from the entire layout
                nets, components = cell.identify_nets()
                
                # recreate the layout
                layout1=pya.Layout()
                topcell1=layout1.create_cell('top')
                for c in components:
                    cell1 = layout1.create_cell(c.cell.name)
                    cells1 = cell1.copy_tree(layout.cell(c.cell.name)) 
                    topcell1.insert(pya.CellInstArray(cell1.cell_index(), c.trans))   
                topcell1.copy_shapes(cell)
                filename = 'development' # top_cell_name
                file_out = export_layout(topcell1, script_dir, filename, relative_path = '.', format='oas', screenshot=True)

                    

