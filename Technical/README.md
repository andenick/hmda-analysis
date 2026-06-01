# Technical Directory

This directory contains all technical implementation details, source code, data files, and archived materials for the HMDA analysis project.

## Structure

### src/
Core source code modules and packages
- Python modules implementing analysis methodologies
- Data processing utilities
- Framework implementations

### data/
Raw and processed data files
- HMDA LAR (Loan Application Register) data files
- Census demographic data
- Geographic boundary files
- Processed datasets

### docs/
Technical documentation
- API documentation
- Methodology guides (DISPARITIES.md, METRICS_AND_IDEAS.md, etc.)
- Handoff documentation
- Segmentation guides

### scripts/
Executable analysis scripts
- Data processing workflows
- Analysis execution scripts
- Utility scripts

### configs/
Configuration files
- Project configuration
- Data source configurations
- Analysis parameters

### tests/
Test files and validation scripts
- Unit tests
- Integration tests
- Validation workflows

### archive/
Historical files and deprecated code
- `consolidated_docs/` - All root-level files from pre-reorganization (40+ Python scripts, markdown docs, notebooks)
- `pre_reorganization_backup_20251003_104227/` - Complete backup before reorganization
- `old_code/` - Legacy implementations
- `web_apps_combined/` - Historical web applications
- `analysis_validation/`, `comparison_data/`, `knowledge_base/` - Historical analysis artifacts
- Various merged folder versions from reorganization

## Key Resources

### Active Development
- Source code: `src/`
- Scripts: `scripts/`
- Configuration: `configs/`
- Documentation: `docs/`

### Historical Reference
All pre-reorganization Python scripts and documentation are preserved in:
- `archive/consolidated_docs/`

This includes:
- Analysis scripts (40+ Python files)
- Project documentation (20+ markdown files)
- Notebooks and data files
- Configuration files

### Data Access
- Current data: `data/`
- Output data: See `../../Output/Data/`

## Development Workflow

1. Configure project in `configs/`
2. Develop modules in `src/`
3. Create analysis scripts in `scripts/`
4. Test using `tests/`
5. Document in `docs/`

## Backup Information

Complete project backup before reorganization:
- Location: `archive/pre_reorganization_backup_20251003_104227/`
- Date: October 3, 2025
- Contains: Full snapshot of key directories and files

---
*Technical implementation following Druck's Shaikh Tonak Pattern*
