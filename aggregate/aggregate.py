
'''
Script to create a layout:

DFB Laser integrated with Photonic Wire Bonds
Splitter tree using 1x2 splitters
Aggregating submitted designs

by Lukas Chrostowski, Sheri, 2022-2025

using SiEPIC-Tools

For more information on scripting:
  https://github.com/SiEPIC/SiEPIC-Tools/wiki/Scripted-Layout
  
usage:
 - run this script, inside KLayout Application, or externally using PyPI package
   - requires siepicfab_ebeam_zep PyPI package 

Install the PDK for develpers:
# cd ... GitHub/SiEPICfab-EBeam-ZEP-PDK
# pip install -e .

 
'''

import siepicfab_ebeam_zep

# Debugging run, or complete
draw_waveguides = True
run_number_designs = 100

# Configuration for the Technology to use
tech = ["SiEPICfab_EBeam_ZEP"]
tech = tech[0]

# Configuration for the arrangement
n_lasers = 3
tree_depth = 4 
die_size = 11e6
die_edge = die_size/2

waveguide_type={'SiEPICfab_Shuksan_PDK':'Strip TE 1310 nm, w=350 nm', 
                'SiEPICfab_EBeam_ZEP':'Strip TE 1310 nm, w=350 nm (core-clad)'}
waveguide_type_routing='Si routing TE 1310 nm (compound waveguide)'

blank_design = "design_ZZZ"  # Python design file, otherwise None for terminator.

waveguide_pitch = 8
dy_gcs = 127e3 # pitch of the fiber array
pad_pitch = 250000
metal_width = 20000
metal_width_laser = 50000
metal_width_laser_heater = 20000

# configuration
top_cell_name = 'Shuksan_2025_02'
cell_Width = 605000
cell_Height = 410000
cell_Gap_Width = 8000
cell_Gap_Height = 8000
cells_rows_per_laser = 4 
cells_columns_per_laser = 4
height_PCM = 3e6  # reserve this space at the top of the chip
laser_dy = (die_size-height_PCM) / (n_lasers+1) # spread out evenly
laser_y = -die_size/2 #  
laser_x = -die_edge  + 2e6
laser_design_offset = 4e6 # distance from the laser to the student design
chip_Width = 8650000
chip_Height1 = 8490000
chip_Height2 = 8780000
br_cutout_x = 7484000
br_cutout_y = 898000
br_cutout2_x = 7855000
br_cutout2_y = 5063000
tr_cutout_x = 7037000
tr_cutout_y = 8494000

filename_out = 'Shuksan'
layers_keep = ['1/0', '1/2', '100/0', '101/0', '1/10', '68/0', '81/0', '10/0', '99/0', '200/0', '11/0', '201/0', '6/0', '998/0']
layer_text = '10/0'
layer_SEM = '200/0'
layer_SEM_allow = ['edXphot1x', 'ELEC413','SiEPIC_Passives']  # which submission folder is allowed to include SEM images
layers_move = [[[31,0],[1,0]]] # move shapes from layer 1 to layer 2
dbu = 0.001
log_siepictools = False
framework_file = 'Framework_2023'
ubc_file = 'UBC_static.oas'


# record processing time
import time
start_time = time.time()
from datetime import datetime
now = datetime.now()




# SiEPIC-Tools initialization
import pya
from pya import *
import SiEPIC
from packaging.version import Version
from SiEPIC._globals import Python_Env, KLAYOUT_VERSION, KLAYOUT_VERSION_3
if Version(SiEPIC.__version__) < Version('0.5.14'):
    raise Exception ('This PDK requires SiEPIC-Tools v0.5.14 or greater.')
from SiEPIC import scripts  
from SiEPIC.utils import get_layout_variables
from SiEPIC.scripts import connect_pins_with_waveguide, connect_cell, zoom_out, export_layout
from SiEPIC.utils.layout import new_layout, floorplan
from SiEPIC.utils import get_technology_by_name
from SiEPIC.extend import to_itype

'''
Create a new layout
with a top cell
and Draw the floor plan
'''    
top_cell, ly = new_layout(tech, top_cell_name, GUI=True, overwrite = True)
layout = ly
dbu = ly.dbu
layerText = pya.LayerInfo(int(layer_text.split('/')[0]), int(layer_text.split('/')[1]))
layerTextN = top_cell.layout().layer(layerText)

TECHNOLOGY = get_technology_by_name(tech)
if TECHNOLOGY['technology_name'] not in tech or not tech in pya.Technology.technology_names():
    raise Exception ('This example needs to be executed in a layout with Technology = %s' % tech)
else:
    waveguide_type = waveguide_type[tech]


'''
# Floorplan
die_edge = int(die_size/2)
box = Box( Point(-die_edge, -die_edge), Point(die_edge, die_edge) )
top_cell.shapes(ly.layer(TECHNOLOGY['FloorPlan'])).insert(box)
'''

def disable_libraries():
    print('Disabling KLayout libraries')
    for l in pya.Library().library_ids():
        print(' - %s' % pya.Library().library_by_id(l).name())
        pya.Library().library_by_id(l).delete()
def enable_libraries():
    import siepicfab_ebeam_zep
    from importlib import reload  
    siepicfab_ebeam_zep = reload(siepicfab_ebeam_zep)
    siepicfab_ebeam_zep.pymacros = reload(siepicfab_ebeam_zep.pymacros)



# path for this python file
import os
path = os.path.dirname(os.path.realpath(__file__))

# Log file
global log_file
log_file = open(os.path.join(path,filename_out+'.txt'), 'w')
def log(text):
    global log_file
    log_file.write(text)
    log_file.write('\n')

log('SiEPIC-Tools %s, layout merge, running KLayout 0.%s.%s ' % (SiEPIC.__version__, KLAYOUT_VERSION,KLAYOUT_VERSION_3) )
current_time = now.strftime("%Y-%m-%d, %H:%M:%S local time")
log("Date: %s" % current_time)

# Load all the GDS/OAS files from the "submissions" folder:
path2 = os.path.abspath(os.path.join(path,"../submissions"))
files_in = []
_, _, files = next(os.walk(path2), (None, None, []))
for f in sorted(files):
    files_in.append(os.path.join(path2,f))

# Load all the GDS/OAS files from the "framework" folder:
path2 = os.path.abspath(os.path.join(path,"../framework"))
_, _, files = next(os.walk(path2), (None, None, []))
for f in sorted(files):
    files_in.append(os.path.join(path2,f))

# Create course cells using the folder name under the top cell
cell_edXphot1x = layout.create_cell("edX")
t = Trans(Trans.R0, 0,0)
top_cell.insert(CellInstArray(cell_edXphot1x.cell_index(), t))
cell_ELEC413 = layout.create_cell("ELEC413")
top_cell.insert(CellInstArray(cell_ELEC413.cell_index(), t))
cell_SiEPIC_Passives = layout.create_cell("SiEPIC_Passives")
top_cell.insert(CellInstArray(cell_SiEPIC_Passives.cell_index(), t))
cell_openEBL = layout.create_cell("openEBL")
top_cell.insert(CellInstArray(cell_openEBL.cell_index(), t))

# Create a date	stamp cell, and add a text label
merge_stamp = '.merged:'+now.strftime("%Y-%m-%d-%H:%M:%S")
cell_date = layout.create_cell(merge_stamp)
text = Text (merge_stamp, Trans(Trans.R0, 0, 0) )
shape = cell_date.shapes(layout.layer(10,0)).insert(text)
top_cell.insert(CellInstArray(cell_date.cell_index(), t))   


# Load all the layouts, without the libraries (no PCells)
disable_libraries()
# Origins for the layouts
x,y = 2.5e6,cell_Height+cell_Gap_Height
design_count = 0
subcell_instances = []
course_cells = []  # list of each of the student designs
cells_course = []  # into which course cell the design should go into
import subprocess
import pandas as pd
for f in [f for f in files_in if '.oas' in f.lower() or '.gds' in f.lower()]:
    basefilename = os.path.basename(f)

    # GitHub Action gets the actual time committed.  This can be done locally
    # via git restore-mtime.  Then we can load the time from the file stamp

    filedate = datetime.fromtimestamp(os.path.getmtime(f)).strftime("%Y%m%d_%H%M")
    log("\nLoading: %s, dated %s" % (os.path.basename(f), filedate))

    # Tried to get it from GitHub but that didn't work:
    # get the time the file was last updated from the Git repository 
    # a = subprocess.run(['git', '-C', os.path.dirname(f), 'log', '-1', '--pretty=%ci',  basefilename], stdout = subprocess.PIPE) 
    # filedate = pd.to_datetime(str(a.stdout.decode("utf-8"))).strftime("%Y%m%d_%H%M")
    #filedate = os.path.getctime(os.path.dirname(f)) # .strftime("%Y%m%d_%H%M")
    
  
    # Load layout  
    layout2 = pya.Layout()
    layout2.read(f)

    if 'elec413' in basefilename.lower():
        course = 'ELEC413'
    elif 'ebeam' in basefilename.lower():
        course = 'edXphot1x'
    elif 'openebl' in basefilename.lower():
        course = 'openEBL'
    elif 'siepic_passives' in basefilename.lower():
        course = 'SiEPIC_Passives'
    else:
        course = 'openEBL'

    cell_course = eval('cell_' + course)
    log("  - course name: %s" % (course) )

    # Check the DBU Database Unit, in case someone changed it, e.g., 5 nm, or 0.1 nm.
    if round(layout2.dbu,10) != dbu:
        log('  - WARNING: The database unit (%s dbu) in the layout does not match the required dbu of %s.' % (layout2.dbu, dbu))
        print('  - WARNING: The database unit (%s dbu) in the layout does not match the required dbu of %s.' % (layout2.dbu, dbu))
        # Step 1: change the DBU to match, but that magnifies the layout
        wrong_dbu = layout2.dbu
        layout2.dbu = dbu
        # Step 2: scale the layout
        try:
            # determine the scaling required
            scaling = round(wrong_dbu / dbu, 10)
            layout2.transform (pya.ICplxTrans(scaling, 0, False, 0, 0))
            log('  - WARNING: Database resolution has been corrected and the layout scaled by %s' % scaling) 
        except:
            print('ERROR IN EBeam_merge.py: Incorrect DBU and scaling unsuccessful')
    
    # check that there is one top cell in the layout
    num_top_cells = len(layout2.top_cells())
    if num_top_cells > 1:
        log('  - layout should only contain one top cell; contains (%s): %s' % (num_top_cells, [c.name for c in layout2.top_cells()]) )
    if num_top_cells == 0:
        log('  - layout does not contain a top cell')

    # Find the top cell
    for cell in layout2.top_cells():
        if framework_file in os.path.basename(f) :
            # Create sub-cell using the filename under top cell
            subcell2 = layout.create_cell(os.path.basename(f)+"_"+filedate)
            t = Trans(Trans.M90, 0,0)
            top_cell.insert(CellInstArray(subcell2.cell_index(), t))
            # copy
            subcell2.copy_tree(layout2.cell(cell.name)) 
            break

        if os.path.basename(f) == ubc_file:
            # Create sub-cell using the filename under top cell
            subcell2 = layout.create_cell(os.path.basename(f)+"_"+filedate)
            t = Trans(Trans.R0, 8780000,8780000)      
            top_cell.insert(CellInstArray(subcell2.cell_index(), t))
            # copy
            subcell2.copy_tree(layout2.cell(cell.name)) 
            break


        if num_top_cells == 1 or cell.name.lower() == 'top' or cell.name.lower() == 'EBeam_':
            log("  - top cell: %s" % cell.name)

            # check layout height
            if cell.bbox().top < cell.bbox().bottom:
                log(' - WARNING: empty layout. Skipping.')
                break
                
            # Create sub-cell using the filename under course cell
            subcell2 = layout.create_cell(os.path.basename(f)+"_"+filedate)
            course_cells.append(subcell2)

            
            # Clear extra layers
            layers_keep2 = [layer_SEM] if course in layer_SEM_allow else []
            for li in layout2.layer_infos():
                if li.to_s() in layers_keep + layers_keep2:
                    log('  - loading layer: %s' % li.to_s())
                else:
                    log('  - deleting layer: %s' % li.to_s())
                    layer_index = layout2.find_layer(li)
                    layout2.delete_layer(layer_index)
                    
            # Delete non-text geometries in the Text layer
            layer_index = layout2.find_layer(int(layer_text.split('/')[0]), int(layer_text.split('/')[1]))
            if type(layer_index) != type(None):
                s = cell.begin_shapes_rec(layer_index)
                shapes_to_delete = []
                while not s.at_end():
                    if s.shape().is_text():
                        text = s.shape().text.string
                        if text.startswith('SiEPIC-Tools'):
                            if log_siepictools:
                                log('  - %s' % s.shape() )
                            s.shape().delete()
                            subcell2.shapes(layerTextN).insert(pya.Text(text, 0, 0))
                        elif text.startswith('opt_in'):
                            log('  - measurement label: %s' % text )
                    else:
                        shapes_to_delete.append( s.shape() )
                    s.next()
                for s in shapes_to_delete:
                    s.delete()

            # bounding box of the cell
            bbox = cell.bbox()
            log('  - bounding box: %s' % bbox.to_s() )
                            
            # Create sub-cell under subcell cell, using user's cell name
            subcell = layout.create_cell(cell.name)
            t = Trans(Trans.R0, -bbox.left,-bbox.bottom)
            subcell_inst = subcell2.insert(CellInstArray(subcell.cell_index(), t)) 
            subcell_instances.append (subcell_inst)
        
            # clip cells
            cell2 = layout2.clip(cell.cell_index(), pya.Box(bbox.left,bbox.bottom,bbox.left+cell_Width,bbox.bottom+cell_Height))
            bbox2 = layout2.cell(cell2).bbox()
            if bbox != bbox2:
                log('  - WARNING: Cell was clipped to maximum size of %s X %s' % (cell_Width, cell_Height) )
                log('  - clipped bounding box: %s' % bbox2.to_s() )

            # copy
            subcell.copy_tree(layout2.cell(cell2))  
            
            log('  - Placed at position: %s, %s' % (x,y) )
            
            # connect to the laser tree  
            from SiEPIC.utils.layout import make_pin
            make_pin(subcell, 'opt_laser', [0,10e3], 350, 'PinRec', 180, debug=False)
              
            #x_out = inst_tree_out[0].pinPoint('opt2').x + 100e3
            # y_out = ytree_y - 934e3 / 2
            
            # intput waveguide:
            #x_in = bbox2.left - 10e3
            #y_in = bbox2.bottom + 10e3
            
            design_count += 1
            cells_course.append (cell_course)
                
            # Measure the height of the cell that was added, and move up
            y += max (cell_Height, subcell.bbox().height()) + cell_Gap_Height
            # move right and bottom when we reach the top of the chip
            if y + cell_Height > chip_Height1 and x == 0:
                y = cell_Height + cell_Gap_Height
                x += cell_Width + cell_Gap_Width
            if y + cell_Height > chip_Height2:
                y = cell_Height + cell_Gap_Height
                x += cell_Width + cell_Gap_Width
            # check top right cutout for PCM
            if x + cell_Width > tr_cutout_x and y + cell_Height > tr_cutout_y:
                # go to the next column
                y = cell_Height + cell_Gap_Height    
                x += cell_Width + cell_Gap_Width
            # Check bottom right cutout for PCM
            if x + cell_Width > br_cutout_x and y < br_cutout_y:
                y = br_cutout_y
            # Check bottom right cutout #2 for PCM
            if x + cell_Width > br_cutout2_x and y < br_cutout2_y:
                y = br_cutout2_y



# Enable libraries, to create waveguides, laser, etc
enable_libraries()



# load the cells from the PDK
if tech == "SiEPICfab_EBeam_ZEP":
    library = tech
    library_beta = "SiEPICfab_EBeam_ZEP_Beta"
    # library_ubc = "SiEPICfab_EBeam_ZEP_UBC"
    cell_y = ly.create_cell('ybranch_te1310', library)
    #cell_splitter = ly.create_cell('splitter_2x2_1310', library)
    #cell_heater = ly.create_cell('wg_heater', library)
    #cell_waveguide = ly.create_cell('ebeam_pcell_taper',library, {
        #'wg_width1': 0.35,
        #'wg_width2': 0.352})
    cell_waveguide = ly.create_cell('Waveguide_Straight',library_beta, {
        'wg_length': 40,
        'wg_width': 350})
    # cell_waveguide = ly.create_cell('w_straight',library)
    #cell_pad = ly.create_cell('ebeam_BondPad', library)
    cell_gcA = ly.create_cell('GC_Air_te1310_BB', library)
    cell_gcB = ly.create_cell('GC_Air_te1310_BB', library)
    cell_terminator = ly.create_cell('terminator_te1310', library)
    cell_laser = ly.create_cell('laser_1310nm_DFB_BB', library_beta)
    metal_layer = "M1"
    cell_taper = ly.create_cell('ebeam_taper_350nm_2000nm_te1310', library_beta)

if not cell_y:
    raise Exception ('Cannot load 1x2 splitter cell; please check the script carefully.')
#if not cell_splitter:
#    raise Exception ('Cannot load 2x2 splitter cell; please check the script carefully.')
if not cell_taper:
    raise Exception ('Cannot load taper cell; please check the script carefully.')
if not cell_gcA:
    raise Exception ('Cannot load grating coupler cell; please check the script carefully.')
if not cell_gcB:
    raise Exception ('Cannot load grating coupler cell; please check the script carefully.')
if not cell_terminator:
    raise Exception ('Cannot load terminator cell; please check the script carefully.')
if not cell_laser:
    raise Exception ('Cannot load laser cell; please check the script carefully.')
#if not cell_pad:
#    raise Exception ('Cannot load bond pad cell; please check the script carefully.')
if not cell_waveguide:
    raise Exception ('Cannot load Waveguide Straight cell; please check the script carefully.')

# Waveguide type:
waveguides = ly.load_Waveguide_types()
waveguide1 = [w for w in waveguides if w['name']==waveguide_type]
if type(waveguide1) == type([]) and len(waveguide1)>0:
    waveguide = waveguide1[0]
else:
    waveguide = waveguides[0]
    print('error: waveguide type not found in PDK waveguides')
    raise Exception('error: waveguide type (%s) not found in PDK waveguides: \n%s' % (waveguide_type, [w['name'] for w in waveguides]))
radius_um = float(waveguide['radius'])
radius = to_itype(waveguide['radius'],ly.dbu)


# laser_height = cell_laser.bbox().height()

inst_tree_out_all = []
for row in range(0, n_lasers):
    
    # laser, place at absolute position
    laser_y += laser_dy
    t = pya.Trans.from_s('r0 %s,%s' % (int(laser_x), int(laser_y)) )
    inst_laser = top_cell.insert(pya.CellInstArray(cell_laser.cell_index(), t))
    
    # splitter tree
    from SiEPIC.utils.layout import y_splitter_tree
    if tree_depth == 4:
        n_x_gc_arrays = 6
        n_y_gc_arrays = 1
        x_tree_offset = 0
        inst_tree_in, inst_tree_out, cell_tree = y_splitter_tree(top_cell, tree_depth=tree_depth, y_splitter_cell=cell_y, library="SiEPICfab_Shuksan_PDK", wg_type=waveguide_type, draw_waveguides=True)
        ytree_x = inst_laser.bbox().right + x_tree_offset
        ytree_y = inst_laser.pinPoint('opt1').y # - cell_tree.bbox().height()/2
        t = Trans(Trans.R0, ytree_x, ytree_y)
        top_cell.insert(CellInstArray(cell_tree.cell_index(), t))
    else:
        # Handle other cases if needed
        raise Exception("Invalid tree_depth value")
    
    inst_tree_out_all += inst_tree_out
    
    # Waveguide, laser to tree:
    connect_pins_with_waveguide(inst_laser, 'opt1', inst_tree_in, 'opt1', waveguide_type=waveguide_type, turtle_A=[10,90]) #turtle_B=[10,-90, 100, 90])

    # instantiate the student cells, and waveguides
    # in batches for each y-tree
    # in a 2D layout array, limited in the height by laser_dy
    position_y0 = laser_y - laser_dy/2
    position_x0 = laser_x+laser_design_offset
    cells_rows_per_laser
    cells_columns_per_laser
    cell_row, cell_column = 0, 0
    for d in range(row*tree_depth**2, min(design_count,(row+1)*tree_depth**2)):
        # Instantiate the course student cell
        position_y = cell_row * (cell_Height + cell_Gap_Height)
        position_x = cell_column * (radius + cell_Width + waveguide_pitch/dbu * cells_rows_per_laser)
        t = Trans(Trans.R0, position_x0 + position_x, position_y0 + position_y)
        cells_course[d].insert(CellInstArray(course_cells[d].cell_index(), t))
        connect_pins_with_waveguide(
            inst_tree_out_all[int(d/2)], 'opt%s'%(2+(d+1)%2), 
            subcell_instances[d], 'opt_laser', 
            waveguide_type=waveguide_type_routing, 
            turtle_B = [ # from the student
                (cells_rows_per_laser-cell_row-1)*waveguide_pitch+radius_um,-90, # left away from student design
                (cells_rows_per_laser-cell_row)*(cell_Height + cell_Gap_Height)*dbu + (cell_row + cell_column*cells_rows_per_laser)*waveguide_pitch,90, # up the column to the top
                100,90, # left towards the laser
            ],
            turtle_A = [ # from the laser
                ((cells_columns_per_laser-cell_column)*cells_rows_per_laser + (cells_rows_per_laser-cell_row))*waveguide_pitch, 90,
                10,-90,
            ],
            verbose=False) 
        #, turtle_A=[10,90]) #turtle_B=[10,-90, 100, 90])
        cell_row += 1
        if cell_row > cells_rows_per_laser-1:
            cell_column += 1
            cell_row = 0
            # break

    from SiEPIC.scripts import connect_cell
    for d in range(min(design_count,(row+1)*tree_depth**2), (row+1)*tree_depth**2):
             
            inst = connect_cell(inst_tree_out_all[int(d/2)], 'opt%s'%(2+(d+1)%2), 
                                cell_terminator, 'pin1')

    

  

# Export for fabrication
import os 
path = os.path.dirname(os.path.realpath(__file__))
filename = 'Shuksan' # top_cell_name
file_out = export_layout(top_cell, path, filename, relative_path = '.', format='oas', screenshot=True)


from SiEPIC._globals import Python_Env
if Python_Env == "Script":
    from SiEPIC.utils import klive
    klive.show(file_out, technology=tech)

# Create an image of the layout
top_cell.image(os.path.join(path,filename+'.png'))

print('Completed %s designs' % design_count)
