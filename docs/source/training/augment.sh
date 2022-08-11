#!/usr/bin/env bash
set -Eeuo pipefail

# This script exists to modify the output from `sphinx-gherkindoc` to better fit
# our needs as training documentation.

FILE=$(mktemp --tmpdir)

# Extend the documentation with our own stylesheet.
echo '.. raw:: html' >> $FILE
echo -e "\n" '    <link href="../_static/training.css" rel="stylesheet">' "\n" >> $FILE

# Give the Given/When/Then steps specific CSS classes, so that we can add spaces
# between sections of the same scenario automatically.
echo '.. role:: gherkin-step-given-keyword' >> $FILE
echo '.. role:: gherkin-step-when-keyword' >> $FILE
echo '.. role:: gherkin-step-then-keyword' >> $FILE
cat $1 >> $FILE
sed -i 's/:gherkin-step-keyword:`Given`/:gherkin-step-given-keyword:`Given`/' $FILE
sed -i 's/:gherkin-step-keyword:`When`/:gherkin-step-when-keyword:`When`/' $FILE
sed -i 's/:gherkin-step-keyword:`Then`/:gherkin-step-then-keyword:`Then`/' $FILE

# Convert the list of steps into a numbered list.
sed -i 's/^|/#./g' $FILE

# Remove "Feature:" from the start of the page title.
sed -i 's/:gherkin-feature-keyword:`Feature:` //' $FILE

mv $FILE $1
