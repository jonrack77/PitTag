# Handling Merge Conflicts for PitTag

When conflicts appear on GitHub, sharing a few details makes it possible to reproduce and fix them locally.

## Information that helps the maintainer

1. **Target branch and commit** – tell us which branch on GitHub you are merging into (for example, `main`) and the latest commit hash on that branch.
2. **Exact error output** – copy the conflict section from GitHub or your Git client so we can see which files and line ranges are involved.
3. **Your branch commit** – provide the head commit hash (or link to the PR) that is encountering conflicts.
4. **Recent upstream changes** – if specific PRs landed recently, mention them so we can pull the same history.

## How to gather the details on GitHub

On the PR page choose **"Resolve conflicts"**, then note the filenames and the conflicting chunks that GitHub highlights. Copying that text into the chat is ideal. Alternatively, click **"View command line instructions"** to get the exact merge command sequence.

## Simulating the conflict locally

To recreate the conflict in this repository clone:

```bash
git fetch origin <target-branch>
git checkout <target-branch>
git pull

git checkout work   # current feature branch
git merge origin/<target-branch>
```

Share any conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) that appear. With those details we can reproduce the issue and craft a patch that applies cleanly.

## Temporary workaround

If you just need to continue testing without merging, keep working on the `work` branch locally. Once we know the conflicting files we can rebase or merge onto the latest upstream code and resolve the conflicts for you.
