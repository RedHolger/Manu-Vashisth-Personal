"""Parametric enclosure generator. Dimensions are a synthetic board, not a product fit claim."""
import argparse,json,math
from pathlib import Path

def parameters(width=65,length=85,board_height=18,clearance=2,wall=2,base=3):
 values=[width,length,board_height,clearance,wall,base]
 if not all(isinstance(v,(int,float)) and math.isfinite(v) and v>0 for v in values):raise ValueError('positive finite dimensions required')
 return dict(width=width,length=length,board_height=board_height,clearance=clearance,wall=wall,base=base,outer_width=width+2*(clearance+wall),outer_length=length+2*(clearance+wall),outer_height=board_height+clearance+base)
def scad(p):
 return f"""// Synthetic-board open-top enclosure; no connector holes or fit validation.
// Dimensions in mm. Bottom and side walls only.
difference() {{
 cube([{p['outer_width']},{p['outer_length']},{p['outer_height']}]);
 translate([{p['wall']},{p['wall']},{p['base']}])
 cube([{p['outer_width']-2*p['wall']},{p['outer_length']-2*p['wall']},{p['outer_height']}]);
}}
"""
def demo(directory):
 p=parameters();out=Path(directory);out.mkdir(parents=True,exist_ok=True);(out/'enclosure.scad').write_text(scad(p));print(json.dumps({'kind':'synthetic geometric design; not mechanical/thermal validation','dimensions_mm':p},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);demo(p.parse_args().output)
