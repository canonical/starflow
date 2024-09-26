# Cache snaps

This action caches snaps on the system, preventing snapd from having to redownload
them from snapcraft.io

# Usage

```yaml
- uses: canonical/starflow/cache-snaps@main
```

# Examples

An example workflow that uses this can be found in [the test workflow](.github/workflows/test-cache-snaps.yaml)
