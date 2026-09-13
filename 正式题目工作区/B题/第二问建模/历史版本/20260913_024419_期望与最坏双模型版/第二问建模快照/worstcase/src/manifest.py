"""Validate frozen baseline inputs and record generated evidence provenance."""
from pathlib import Path
import hashlib,json,datetime,platform,subprocess,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    snapshot=json.loads((ROOT/'sources_snapshot.json').read_text())
    for name,h in snapshot.items():
        assert sha(ROOT/name)==h, 'Baseline source changed: '+name
    comp=json.loads((ROOT/'runs/R001/comparison.json').read_text())
    glob=json.loads((ROOT/'verification/global_bound_0001.json').read_text())
    assert glob['completed'] and glob['gap_m']<=.001
    geo=json.loads((ROOT/'verification/independent_geometry.json').read_text())
    conv=json.loads((ROOT/'verification/convergence.json').read_text())
    candidates=json.loads((ROOT/'runs/R001/candidates_summary.json').read_text())
    mc=json.loads((ROOT/'verification/minimax_monte_carlo.json').read_text())
    mc_z=(mc['mean_radius']-comp['results']['minimax']['uniform_prior_expectation']['E_radius_loss'])/mc['radius_standard_error']
    assert mc['invalid']==0 and abs(mc_z)<4
    files={str(p.relative_to(ROOT)):sha(p) for p in ROOT.rglob('*') if p.is_file() and p.name!='manifest.json' and p.suffix not in ['.stdout','.stderr'] and '__pycache__' not in p.parts}
    record={'model':'Q2-WC-U-v01','run':'R001','status':'numerically_solved_and_verified_not_formally_adopted',
        'updated_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
        'reference_geometry':{'first_point':[0,0],'first_bearing_deg':0,'first_radius_min_exclusive_m':5,'reception_range_m':[1000,1500],'angular_error_bound_deg':1,'optical_range_m':20},
        'objective':'supremum of remaining MEC radius over all compatible strong/no-signal/normal feedbacks, with guaranteed local optical localization assigned zero',
        'distributions_used_for_minimax':False,
        'distribution_for_cross_evaluation':'preserved uniform joint prior with first-observation conditioning',
        'best_candidate':comp['results']['minimax']['q'],
        'fixed_point_worst_bound_m':[comp['results']['minimax']['strict_worst']['worst_lower'],comp['results']['minimax']['strict_worst']['worst_upper']],
        'global_lower_bound_m':glob['global_lower_bound'],'global_numerical_gap_m':glob['gap_m'],
        'machine_rigorous_interval_arithmetic_certificate':False,
        'global_bound_method':'common-feedback source subsets over circumscribed detector-cell disks; double precision with numerical margins',
        'independent_geometry_cases':len(geo),'max_independent_sample_outside_m':max(g['max_sample_outside_m'] for g in geo),
        'cell_bound_cross_checks':candidates['cell_property_check_count'],
        'monte_carlo_samples':mc['n'],'monte_carlo_radius_z_score':mc_z,'monte_carlo_invalid_geometry':mc['invalid'],
        'max_expected_radius_convergence_difference_m':max(c['expected_radius_difference'] for c in conv),
        'candidate_grid_count_north':candidates['accepted_points_north'],
        'python':sys.version,'numpy':np.__version__,'platform':platform.platform(),
        'compiler':subprocess.check_output(['clang++','--version'],text=True).splitlines()[0],
        'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'frozen_baseline_sources':snapshot,'output_and_code_sha256':files,
        'reproduce_command':'python3 src/reproduce.py','commit_or_push_performed':False}
    (ROOT/'manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    print('Manifest written; all frozen baseline source hashes match.')
if __name__=='__main__':main()
