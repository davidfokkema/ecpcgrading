__grading=$(which grading);

function gradestart {
    eval cd $($__grading shell startpath);
    eval conda activate $($__grading shell startenv);
};

function gradenext {
    eval cd $($__grading shell nextpath);
    eval conda activate $($__grading shell nextenv);
};