__grading=$(which grading);

function gradestart {
    eval cd \"$($__grading shell startpath)\";
    eval conda activate $($__grading shell thisenv);
};

function gradenext {
    eval cd \"$($__grading shell nextpath)\";
    eval conda activate $($__grading shell thisenv);
};

function gradeprev {
    eval cd \"$($__grading shell prevpath)\";
    eval conda activate $($__grading shell thisenv);
};

function gradethis {
    eval cd \"$($__grading shell thispath)\";
    eval conda activate $($__grading shell thisenv);
};