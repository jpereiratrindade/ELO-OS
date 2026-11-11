# SPDX-License-Identifier: GPL-3.0-only
"""Adapt the existing ELO Studio publication actions for ELO-OS deployment."""
from pathlib import Path
import re


def publication_actions(javascript):
    replacements = [
        ("const publishResponse = await fetch(`/api/packages/${encodeURIComponent(plan.bundle_id)}/activate`, { method: 'POST' });\n      const result = await publishResponse.json();",
         "const result = await window.eloStudioPublishing.publish(plan.bundle_id);\n      if (result.cancelled) { showNotice('Publicação cancelada', 'A versão anterior foi preservada.'); return; }"),
        ("const res = await fetch('/api/publish', {\n          method: 'POST',\n          headers: { 'Content-Type': 'application/json' },\n          body: JSON.stringify({ bundle_id: selectedPackageId || '' })\n        });\n        const data = await res.json();",
         "const data = await window.eloStudioPublishing.publish(currentStatus?.active_bundle?.bundle_id || selectedPackageId || '');\n        if (data.cancelled) { showNotice('Publicação cancelada', 'A versão anterior foi preservada.'); return; }"),
        ("const actRes = await fetch(`/api/packages/${encodeURIComponent(bundleId)}/activate`, { method: 'POST' });\n            const actData = await actRes.json();",
         "const actData = await window.eloStudioPublishing.publish(bundleId);\n            if (actData.cancelled) { showNotice('Publicação cancelada', 'O rascunho foi salvo; a versão anterior foi preservada.'); return true; }")]
    for old, new in replacements:
        if javascript.count(old) != 1:
            raise ValueError('ELO Studio publication actions changed; review adapter before deploying')
        javascript = javascript.replace(old, new)
    helper = (Path(__file__).resolve().parents[1] / 'web/distribution/studio-publishing.js').read_text()
    intake = (Path(__file__).resolve().parents[1] / 'web/distribution/studio-consumables.js').read_text()
    return helper + '\n' + intake + '\n' + javascript


def versioned_assets(html):
    # A visible deployed release must load its matching script after a normal reload.
    return re.sub(r'src="app\.js(?:\?[^\"]*)?"', 'src="app.js?v=sister-intake-20261111-2"', html)
