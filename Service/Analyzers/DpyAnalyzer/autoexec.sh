echo "Starting DPy analysis on before and after change files..."

echo "Running DPy analysis on before change files..."
./run_dpy_all.sh -i ../1.\ Collecting_file_changed_by_commits/before_change -o ../dpy_reports/before -j 8

echo "--------------------------------------------------"
echo "Running DPy analysis on after change files..."
./run_dpy_all.sh -i ../1.\ Collecting_file_changed_by_commits/after_change -o ../dpy_reports/after -j 8

echo "--------------------------------------------------"
echo "Done!"    