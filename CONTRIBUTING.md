# Contributing to HBntory

## Team workflow

HBntory uses GitHub Flow. The `main` branch must always remain functional, and direct pushes to `main` are forbidden. The project does not use a `develop` branch.

Every task must have a GitHub Issue. Each Issue is assigned to either Sébastien or Ulysse. One person works on the related feature branch, and the other person reviews the Pull Request. Both team members are repository collaborators, so forks are not required.

## Clone the repository

```bash
git clone https://github.com/S3333B/hbntory-inventory-platform.git
cd hbntory-inventory-platform
```

## Start a new task

Start from an up-to-date `main` branch:

```bash
git switch main
git pull --ff-only origin main
git switch -c feat/12-short-description
```

In this example, `12` is the GitHub Issue number. Replace it with the number of the Issue being implemented.

## Branch naming

Use the prefix that matches the type of work:

- `feat/12-feature-name`
- `fix/12-bug-name`
- `docs/12-document-name`
- `test/12-test-name`
- `chore/12-maintenance-name`

Branch names must use lowercase words separated by hyphens.

## Make a commit

Inspect the working tree, stage only the relevant files, and create an explicit commit:

```bash
git status
git add path/to/modified-file
git commit -m "feat(backoffice): add stock management form"
```

Contributors must:

- inspect `git status` before committing;
- add only files related to the current Issue;
- avoid `git add .` when unrelated files are present;
- write short and explicit commit messages;
- never commit `.env`, passwords, API keys, or tokens.

Use one of these commit types:

- `feat` for a new feature;
- `fix` for a bug fix;
- `docs` for documentation;
- `test` for tests;
- `refactor` for an internal code change without a feature or bug fix;
- `chore` for maintenance work.

## Push the branch

Push the feature branch to GitHub:

```bash
git push -u origin feat/12-short-description
```

## Open a Pull Request

Every Pull Request must:

- target `main`;
- contain a clear description of the change;
- include `Closes #12`, using the correct Issue number;
- explain how to test the change;
- contain screenshots when an interface changes;
- be assigned to the other team member for review.

## Review rules

The reviewer must check:

- the requested functionality;
- authorization rules where applicable;
- error handling;
- tests;
- documentation;
- absence of secrets;
- absence of unrelated modifications.

After approval and successful validation, the Pull Request must use **Squash and merge**.

## After the merge

Update the local `main` branch and remove the merged local feature branch:

```bash
git switch main
git pull --ff-only origin main
git branch -d feat/12-short-description
```

## Synchronize an active branch

If `main` changes while a feature branch is active, fetch and merge the latest remote `main`:

```bash
git fetch origin
git merge origin/main
```

Resolve conflicts carefully. Review every conflict, run the relevant tests, and inspect the result before pushing the branch again.

## GitHub Project workflow

The GitHub Project uses four columns:

- **To do**
- **In progress**
- **In review**
- **Done**

Move an Issue to **In progress** when development starts. Move it to **In review** when its Pull Request is opened. Move it to **Done** only after the Pull Request is merged. Normally, each team member should have only one main Issue in progress at a time.

## Prohibited actions

The following actions are prohibited:

- pushing directly to `main`;
- force-pushing to `main`;
- working together on the same feature branch;
- committing `.env`;
- committing generated caches or virtual environments;
- deleting or replacing another member's work;
- merging one's own Pull Request without review, except during an agreed emergency;
- using destructive commands such as `git reset --hard` without team agreement.
