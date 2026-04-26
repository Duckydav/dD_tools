"""
Mattes_Inclusion - Dynamic DIMATTE Layer Remapper for Nuke 14+
=============================================================
Scans input EXR for DIMATTE_* layers, excludes *_eyes variants,
remaps kept layers to matte1, matte2, matte3... and outputs
only rgb + matteN channels.

Usage:
------
  # From Script Editor or menu.py:
  import mattes_inclusion
  mattes_inclusion.create()

  # Then click "Refresh Mattes" on the node panel after connecting input.

Integration in menu.py:
-----------------------
  import mattes_inclusion
  toolbar = nuke.menu('Nodes')
  toolbar.addCommand('dD_Tools/Mattes_Inclusion', 'mattes_inclusion.create()')
"""

import nuke


# ─────────────────────────────────────────────
#  Core refresh logic (called by the button)
# ─────────────────────────────────────────────

def refresh(grp=None):
    """
    Scans the Group's input for DIMATTE_* layers,
    rebuilds internal nodes to remap them to matte1..N,
    and strips everything else except rgb.
    """
    grp = grp or nuke.thisNode()

    # --- Validate input ---
    if not grp.input(0):
        nuke.message("Aucun input connecte.")
        return

    try:
        channels = grp.input(0).channels()
    except Exception:
        nuke.message("Impossible de lire les channels de l'input.")
        return

    if not channels:
        nuke.message("L'input ne contient aucun channel.")
        return

    # --- Collect DIMATTE layers, exclude *_eyes ---
    dimatte_set = set()
    for ch in channels:
        layer = ch.split('.')[0]
        if layer.startswith('DIMATTE_') and not layer.lower().endswith('_eyes'):
            dimatte_set.add(layer)

    dimatte_layers = sorted(dimatte_set)

    if not dimatte_layers:
        nuke.message(
            "Aucun layer DIMATTE_ trouve dans l'input\n"
            "(les layers *_eyes sont exclus).\n\n"
            "Layers disponibles :\n" +
            '\n'.join(sorted(set(c.split('.')[0] for c in channels)))
        )
        return

    # --- Rebuild internal graph ---
    grp.begin()

    # Delete everything except Input1 / Output1
    for n in nuke.allNodes():
        if n.name() not in ('Input1', 'Output1'):
            nuke.delete(n)

    inp = nuke.toNode('Input1')
    out = nuke.toNode('Output1')

    # --- Copy chain : DIMATTE_X -> matteN ---
    last = inp
    matte_names = []

    for i, dl in enumerate(dimatte_layers, 1):
        mn = 'matte{}'.format(i)

        # Register the new layer globally
        nuke.tcl('add_layer {{{0} {0}.red {0}.green {0}.blue {0}.alpha}}'.format(mn))

        c = nuke.nodes.Copy()
        c.setInput(0, last)   # B = accumulated stream
        c.setInput(1, inp)    # A = original input (source of DIMATTE channels)

        c['from0'].setValue('{}.red'.format(dl))
        c['to0'].setValue('{}.red'.format(mn))
        c['from1'].setValue('{}.green'.format(dl))
        c['to1'].setValue('{}.green'.format(mn))
        c['from2'].setValue('{}.blue'.format(dl))
        c['to2'].setValue('{}.blue'.format(mn))
        c['from3'].setValue('{}.alpha'.format(dl))
        c['to3'].setValue('{}.alpha'.format(mn))

        c['name'].setValue('Copy_{}'.format(mn))
        c['label'].setValue('{}\n-> {}'.format(dl, mn))

        matte_names.append(mn)
        last = c

    # --- Remove(keep) : only rgb + matteN ---
    # Nuke Remove node has 4 channel slots max, so batch in groups of 4
    layers_to_keep = ['rgb'] + matte_names
    batches = [layers_to_keep[x:x + 4] for x in range(0, len(layers_to_keep), 4)]

    remove_nodes = []
    for bi, batch in enumerate(batches):
        r = nuke.nodes.Remove()
        r.setInput(0, last)
        r['operation'].setValue('keep')
        for j, ly in enumerate(batch):
            key = 'channels' if j == 0 else 'channels{}'.format(j + 1)
            r[key].setValue(ly)
        r['name'].setValue('Keep_{}'.format(bi + 1))
        remove_nodes.append(r)

    # Chain Remove outputs via Merge(also_merge all)
    final = remove_nodes[0]
    for rn in remove_nodes[1:]:
        m = nuke.nodes.Merge2()
        m['also_merge'].setValue('all')
        m['Achannels'].setValue('none')
        m['Bchannels'].setValue('none')
        m['output'].setValue('none')
        m.setInput(0, final)  # B
        m.setInput(1, rn)     # A
        m['name'].setValue('MergeKeep')
        final = m

    out.setInput(0, final)
    grp.end()

    # --- Update node UI ---
    mapping_lines = []
    for i, dl in enumerate(dimatte_layers):
        mapping_lines.append('  {}  ->  matte{}'.format(dl, i + 1))
    mapping_text = '\n'.join(mapping_lines)

    if 'mapping_info' in grp.knobs():
        grp['mapping_info'].setValue(mapping_text)

    grp['label'].setValue('{} mattes'.format(len(dimatte_layers)))

    nuke.message(
        '{} layers DIMATTE remappes :\n\n{}'.format(len(dimatte_layers), mapping_text)
    )


# ─────────────────────────────────────────────
#  Enable All Channels on EXR Write nodes
# ─────────────────────────────────────────────

def set_exr_all():
    """Force all EXR Write nodes to output 'all' channels."""
    changed = []
    for w in nuke.root().nodes():
        if w.Class() != 'Write':
            continue
        ft = w['file_type'].value() if 'file_type' in w.knobs() else ''
        if str(ft).lower() == 'exr' and 'channels' in w.knobs():
            w['channels'].setValue('all')
            changed.append(w.name())

    if changed:
        nuke.message("Channels -> all :\n" + "\n".join(changed))
    else:
        nuke.message("Aucun Write EXR trouve.")


# ─────────────────────────────────────────────
#  Node creation
# ─────────────────────────────────────────────

# Button callback code (self-contained, embedded in the gizmo knob)
_REFRESH_BTN = (
    "import sys, nuke\n"
    "# Try importing the module; fall back to inline if unavailable\n"
    "try:\n"
    "    import mattes_inclusion\n"
    "    reload(mattes_inclusion)\n"
    "    mattes_inclusion.refresh(nuke.thisNode())\n"
    "except ImportError:\n"
    "    nuke.message('Module mattes_inclusion.py introuvable dans le NUKE_PATH.\\n'\n"
    "                 'Placez-le dans votre dossier .nuke ou pipeline.')\n"
)

_SET_EXR_BTN = (
    "try:\n"
    "    import mattes_inclusion\n"
    "    mattes_inclusion.set_exr_all()\n"
    "except ImportError:\n"
    "    nuke.message('Module mattes_inclusion.py introuvable.')\n"
)


def create():
    """Create a Mattes_Inclusion Group node in the current Nuke script."""

    grp = nuke.createNode('Group', inpanel=True)
    grp['name'].setValue('Mattes_Inclusion')
    grp['tile_color'].setValue(0x632929ff)

    # --- User tab with knobs ---
    tab = nuke.Tab_Knob('User')
    grp.addKnob(tab)

    # Divider
    div0 = nuke.Text_Knob('div0', '', '<b>Mattes Inclusion</b>  —  DIMATTE remapper')
    grp.addKnob(div0)

    # Refresh button
    btn_refresh = nuke.PyScript_Knob('refresh_btn', ' Refresh Mattes ', _REFRESH_BTN)
    btn_refresh.setFlag(nuke.STARTLINE)
    grp.addKnob(btn_refresh)

    # Info text
    info = nuke.Text_Knob('refresh_info', '',
                          '<span style="color:#888">Connecter un input EXR puis cliquer Refresh.</span>')
    grp.addKnob(info)

    # Separator
    div1 = nuke.Text_Knob('div1', '')
    grp.addKnob(div1)

    # Mapping display
    mapping = nuke.Multiline_Eval_String_Knob('mapping_info', 'Mapping')
    mapping.setEnabled(False)
    grp.addKnob(mapping)

    # Separator
    div2 = nuke.Text_Knob('div2', '')
    grp.addKnob(div2)

    # Set EXR All button
    btn_exr = nuke.PyScript_Knob('set_exr_all', 'Enable All Channels (Writes)', _SET_EXR_BTN)
    btn_exr.setFlag(nuke.STARTLINE)
    grp.addKnob(btn_exr)

    # --- Create Input / Output inside the group ---
    grp.begin()
    inp = nuke.createNode('Input', inpanel=False)
    inp['name'].setValue('Input1')
    outp = nuke.createNode('Output', inpanel=False)
    outp['name'].setValue('Output1')
    outp.setInput(0, inp)
    grp.end()

    return grp


# ─────────────────────────────────────────────
#  Direct execution from Script Editor
# ─────────────────────────────────────────────

if __name__ == '__main__' or nuke.env.get('gui', False):
    pass  # Import only — call create() explicitly
