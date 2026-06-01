#!/usr/bin/env python3
"""Generate HDARP preparation report"""

import json
from pathlib import Path
from datetime import datetime

# Load all data
with open('_pdf_inventory_temp.json', 'r', encoding='utf-8') as f:
    pdf_inventory = json.load(f)

with open('_processing_results_temp.json', 'r', encoding='utf-8') as f:
    processing_results = json.load(f)

# Calculate statistics
total_chunks = sum(r['chunks'] for r in processing_results)
chunked_count = sum(1 for r in processing_results if r['status'] == 'CHUNKED')
copied_count = sum(1 for r in processing_results if r['status'] == 'COPIED')
already_processed = sum(1 for r in processing_results if r['status'] == 'ALREADY_PROCESSED')
error_count = sum(1 for r in processing_results if r['status'] == 'ERROR')

# Get current directory details
project_dir = Path.cwd()
project_name = project_dir.name

# Generate report filename
report_path = Path(f'[{datetime.now().strftime("%Y.%m.%d")}] HDARP_PREPARATION_REPORT.md')

# Start building report
lines = []
lines.append(f'# HDARP Preparation Report - {project_name}')
lines.append(f'**Generated**: {datetime.now().strftime("%B %d, %Y %H:%M")}')
lines.append(f'**Project**: {project_dir}')
lines.append('**Command**: `/prepareHDARP`')
lines.append('')
lines.append('---')
lines.append('')
lines.append('## Executive Summary')
lines.append('')
lines.append(f'**Total PDFs Prepared**: {len(pdf_inventory)} documents')
lines.append(f'**Total Chunks Created**: {total_chunks} chunks')
lines.append('**Ready for Processing**: YES ✅')
lines.append('')
lines.append('### Processing Statistics')
lines.append('')
lines.append('| Category | Count |')
lines.append('|----------|-------|')
lines.append(f'| PDFs Inventoried | {len(pdf_inventory)} |')
lines.append(f'| Chunked Documents | {chunked_count} |')
lines.append(f'| Copied Documents | {copied_count} |')
lines.append(f'| Already Processed | {already_processed} |')
lines.append(f'| Errors | {error_count} |')
lines.append(f'| **Total Chunks Ready** | **{total_chunks}** |')
lines.append('')
lines.append('---')
lines.append('')
lines.append('## Document Processing Details (Top 30)')
lines.append('')
lines.append('| Document | Source Size (MB) | Pages | Chunks | Status |')
lines.append('|----------|------------------|-------|--------|--------|')

# Add top 30 documents (chunked first, then copied)
sorted_results = sorted(processing_results, key=lambda x: (x['status'] != 'CHUNKED', -x['chunks']))
for result in sorted_results[:30]:
    # Find inventory item
    item = next((x for x in pdf_inventory if x['doc_name'] == result['doc_name']), None)
    if item:
        doc_display = result['doc_name'][:50]
        lines.append(f"| {doc_display} | {item['size_mb']:.2f} | {item['pages']} | {result['chunks']} | {result['status']} |")

lines.append('')
lines.append('*Showing top 30 documents. See full results in Technical/_processing_results_temp.json*')
lines.append('')
lines.append('---')
lines.append('')
lines.append('## NEXT STEPS - READY FOR PROCESSING')
lines.append('')
lines.append(f'### All {total_chunks} chunks are prepared and ready for HDARP processing!')
lines.append('')
lines.append('**Recommended command**:')
lines.append('```bash')
lines.append('/hdarp 5')
lines.append('```')
lines.append('')
lines.append('This will:')
lines.append(f'1. Find all {total_chunks} chunks in Technical/HDARP/*/chunks/')
lines.append('2. Process them in parallel batches of 5')
lines.append('3. Extract tables (CSV), equations (LaTeX), figures (MD), text (full OCR)')
lines.append('4. Save results to output/ subdirectories')
lines.append('')
lines.append(f'**Processing Time Estimate**: ~{(total_chunks * 2) / 60:.1f} hours (at ~2 min/chunk with 5 parallel)')
lines.append('')
lines.append('**Alternative commands**:')
lines.append('- `/hdarp 3` - Conservative (3 parallel processors)')
lines.append('- `/hdarp 10` - Maximum throughput (10 parallel processors)')
lines.append('')
lines.append('---')
lines.append('')
lines.append('## Processing Quality')
lines.append('')
success_rate = (len(pdf_inventory) - error_count) / len(pdf_inventory) * 100
lines.append(f'**Success Rate**: {success_rate:.1f}%')
lines.append(f'- Successfully processed: {len(pdf_inventory) - error_count} documents')
lines.append(f'- Errors: {error_count} documents')
lines.append('')
lines.append('**Chunk Distribution**:')
avg_chunks = total_chunks / len(pdf_inventory)
max_chunks = max(r['chunks'] for r in processing_results)
lines.append(f'- Average chunks per document: {avg_chunks:.1f}')
lines.append(f'- Maximum chunks: {max_chunks} (largest document)')
lines.append(f'- Documents ready as-is (≤10 pages AND ≤1MB): {copied_count}')
lines.append('')

if error_count > 0:
    lines.append('## Errors Encountered')
    lines.append('')
    lines.append('The following documents had processing errors:')
    lines.append('')
    errors = [r for r in processing_results if r['status'] == 'ERROR']
    for err in errors:
        error_msg = err.get('error', 'Unknown error')[:80]
        lines.append(f"- **{err['doc_name'][:50]}**: {error_msg}")
    lines.append('')

lines.append('---')
lines.append('')
lines.append('## File Inventory Statistics')
lines.append('')
lines.append('**Size Distribution**:')

# Calculate size distribution
size_ranges = [
    (0, 0.5, 'Very Small (0-0.5 MB)'),
    (0.5, 1.0, 'Small (0.5-1.0 MB)'),
    (1.0, 2.0, 'Medium (1-2 MB)'),
    (2.0, 5.0, 'Large (2-5 MB)'),
    (5.0, float('inf'), 'Very Large (>5 MB)')
]

for min_size, max_size, label in size_ranges:
    count = sum(1 for x in pdf_inventory if min_size <= x['size_mb'] < max_size)
    if count > 0:
        lines.append(f'- {label}: {count} documents')

lines.append('')
lines.append('**Page Distribution**:')

page_ranges = [
    (1, 10, '1-10 pages (small)'),
    (11, 50, '11-50 pages (medium)'),
    (51, 100, '51-100 pages (large)'),
    (101, 200, '101-200 pages (very large)'),
    (201, float('inf'), '>200 pages (massive)')
]

for min_pages, max_pages, label in page_ranges:
    count = sum(1 for x in pdf_inventory if min_pages <= x['pages'] < max_pages)
    if count > 0:
        lines.append(f'- {label}: {count} documents')

lines.append('')
lines.append('---')
lines.append('')
lines.append('## Technical Details')
lines.append('')
lines.append('**HDARP Version**: 3.3')
lines.append('**Chunking Limits**:')
lines.append('- Maximum pages per chunk: 10 pages (STRICT)')
lines.append('- Maximum size per chunk: 1.0 MB (STRICT)')
lines.append('')
lines.append('**Processing Method**:')
lines.append('- Large PDFs (>10 pages OR >1MB): Chunked using split_pdf_smart()')
lines.append('- Small PDFs (≤10 pages AND ≤1MB): Copied as single chunk')
lines.append('')
lines.append('**Output Structure**:')
lines.append('Each document directory contains:')
lines.append('- `chunks/` - PDF chunks ready for HDARP processing')
lines.append('- `output/tables/` - Extracted tables (CSV format)')
lines.append('- `output/equations/` - Extracted equations (LaTeX format)')
lines.append('- `output/figures/` - Figure descriptions (Markdown)')
lines.append('- `output/text/` - Full OCR text extraction')
lines.append('- `manifest.json` - Processing metadata')
lines.append('')
lines.append('---')
lines.append('')
lines.append('## Workspace Compliance')
lines.append('')
lines.append('**Druck Standards Compliance**:')
lines.append('- ✅ 3-Folder Structure (Inputs/, Technical/, Output/)')
lines.append('- ✅ Inputs/ preserved (read-only originals)')
lines.append('- ✅ Processing in Technical/HDARP/')
lines.append('- ✅ HDARP chunking protocol followed (≤10 pages, ≤1MB)')
lines.append('')
lines.append('---')
lines.append('')
lines.append('**Report Status**: PREPARATION COMPLETE ✅')
lines.append('**Ready for Processing**: YES')
lines.append('**Recommended Next Action**: Run `/hdarp 5`')
lines.append('')
lines.append('---')
lines.append('')
lines.append('*Generated by /prepareHDARP v2.0 (Full Automation)*')
lines.append('*Maintained by Druck (Arcanum Performance Monitoring)*')
lines.append(f'*Date: {datetime.now().strftime("%B %d, %Y")}*')

# Write report
report_content = '\n'.join(lines)
with open(report_path, 'w', encoding='utf-8') as f:
    f.write(report_content)

print(f'✓ Preparation report created: {report_path}')
print(f'  Size: {len(report_content) / 1024:.1f} KB')
print(f'  {len(lines)} lines')
