# Release Checklist

## Pre-Release Testing

### ✅ Smoke Tests
- [ ] `python scripts/smoke_stack.py` - All services responding
- [ ] `python scripts/smoke_tc_claim_guard.py` - TranceCreate claim_guard working
- [ ] `python scripts/smoke_trancespell.py` - TranceSpell detection working

### ✅ Health & Meta Endpoints
- [ ] Guard `/meta` shows version & commit
- [ ] Worker `/health` shows version & commit  
- [ ] TranceCreate `/health` shows version & commit
- [ ] TranceSpell `/health` shows version & commit

### ✅ Core Functionality
- [ ] claim_guard trace visible in TranceCreate responses
- [ ] Invariant protection working (placeholders, HTML, numbers)
- [ ] All services start without errors
- [ ] Ports match `/config/ports.json` configuration

### ✅ Repository Health
- [ ] No large artifacts in git (models, binaries)
- [ ] `.gitignore` properly excludes heavy files
- [ ] All services use shared libraries from `/libs/trance_common/`
- [ ] No API shape breaks (only additive fields)

## Release Process

### 1. Version Bump
```bash
# Bump version and update changelog
python scripts/bump_version.py patch "Release description"
```

### 2. Final Testing
- [ ] Run all smoke tests again
- [ ] Verify version appears in all service endpoints
- [ ] Check CHANGELOG.md is properly updated

### 3. Commit & Tag
```bash
# Commit changes
git add .
git commit -m "Release vX.Y.Z"

# Tag release (optional)
git tag vX.Y.Z
```

## Post-Release

### ✅ Verification
- [ ] All services start with new version
- [ ] Health endpoints show correct version
- [ ] Documentation reflects current version
- [ ] No regressions in core functionality

### ✅ Documentation
- [ ] Update version in README files if needed
- [ ] Verify CHANGELOG.md entries are accurate
- [ ] Check that all new features are documented

## Emergency Rollback

If issues are discovered post-release:

1. **Immediate**: Revert to previous version tag
2. **Investigation**: Identify root cause
3. **Fix**: Apply fixes and test thoroughly
4. **Re-release**: Bump patch version with fix description
