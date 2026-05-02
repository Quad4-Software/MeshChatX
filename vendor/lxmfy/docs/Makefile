# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= poetry run sphinx-build
SOURCEDIR     = source
BUILDDIR      = build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile serve gettext pot html-% epub-% latexpdf-% text-%

serve: html
	@echo "Starting local server at http://localhost:8000"
	@cd $(BUILDDIR)/html && python -m http.server 8000

# Translation targets
gettext:
	@$(SPHINXBUILD) -b gettext $(SOURCEDIR) $(BUILDDIR)/gettext

pot: gettext
	@echo "Translatable strings extracted to $(BUILDDIR)/gettext"

# Generic language build targets
# Usage: make html-ru, make epub-fr, etc.
html-%: gettext
	@$(SPHINXBUILD) -b html -D language=$* $(SOURCEDIR) $(BUILDDIR)/html/$*

epub-%: gettext
	@$(SPHINXBUILD) -b epub -D language=$* $(SOURCEDIR) $(BUILDDIR)/epub/$*

latexpdf-%: gettext
	@$(SPHINXBUILD) -b latex -D language=$* $(SOURCEDIR) $(BUILDDIR)/latex/$*
	@$(MAKE) -C $(BUILDDIR)/latex/$*

text-%: gettext
	@$(SPHINXBUILD) -b text -D language=$* $(SOURCEDIR) $(BUILDDIR)/text/$*

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
