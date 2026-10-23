"""Run extract, project and check in order."""
from layout_constraints import check, extract, project

if __name__ == "__main__":
    extract.main()
    project.main()
    check.main()
