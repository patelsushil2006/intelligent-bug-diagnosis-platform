document.addEventListener("DOMContentLoaded", function () {

    // Confirm before deleting a bug history record
    const deleteForms = document.querySelectorAll(".delete-form");

    deleteForms.forEach(function (form) {
        form.addEventListener("submit", function (event) {
            const confirmed = confirm(
                "Are you sure you want to delete this record?"
            );

            if (!confirmed) {
                event.preventDefault();
            }
        });
    });


    // Copy corrected code to clipboard
    const copyButton = document.getElementById("copyCodeButton");
    const correctedCode = document.getElementById("correctedCode");

    if (copyButton && correctedCode) {
        copyButton.addEventListener("click", async function () {
            const code = correctedCode.textContent;

            try {
                await navigator.clipboard.writeText(code);
                copyButton.textContent = "Copied!";

                setTimeout(function () {
                    copyButton.textContent = "Copy Corrected Code";
                }, 2000);

            } catch (error) {
                alert("Unable to copy code. Please copy it manually.");
            }
        });
    }


    // Show selected source filename
    const fileInput = document.getElementById("code_file");
    const fileNameDisplay = document.getElementById("fileName");

    if (fileInput && fileNameDisplay) {
        fileInput.addEventListener("change", function () {
            if (fileInput.files.length > 0) {
                fileNameDisplay.textContent =
                    "Selected file: " + fileInput.files[0].name;
            } else {
                fileNameDisplay.textContent = "";
            }
        });
    }


    // Confirm before submitting code for analysis
    const analysisForm = document.getElementById("analysisForm");

    if (analysisForm) {
        analysisForm.addEventListener("submit", function (event) {
            const codeInput = document.getElementById("code");

            const hasCode = codeInput && codeInput.value.trim() !== "";
            const hasFile = fileInput && fileInput.files.length > 0;

            if (!hasCode && !hasFile) {
                event.preventDefault();
                alert("Please paste code or select a source file.");
            }
        });
    }

});
