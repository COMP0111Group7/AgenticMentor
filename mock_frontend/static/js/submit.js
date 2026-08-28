document.addEventListener('DOMContentLoaded', function() {
  const codebaseDropzone = document.getElementById('codebaseDropzone');
  const codebaseInput = document.getElementById('codebaseInput');
  const codebaseFileName = document.getElementById('codebaseFileName');

  const docsDropzone = document.getElementById('docsDropzone');
  const docsInput = document.getElementById('docsInput');
  const docsFileName = document.getElementById('docsFileName');

  const submitBtn = document.getElementById('submitBtn');
  const reviewingCard = document.getElementById('reviewingCard');

  let codebaseFile = null;
  let docsFile = null;

  // Codebase dropzone handlers
  setupDropzone(codebaseDropzone, codebaseInput, (file) => {
    codebaseFile = file;
    codebaseFileName.textContent = file.name;
    codebaseFileName.classList.remove('d-none');
    updateSubmitButton();
  });

  // Docs dropzone handlers
  setupDropzone(docsDropzone, docsInput, (file) => {
    docsFile = file;
    docsFileName.textContent = file.name;
    docsFileName.classList.remove('d-none');
    updateSubmitButton();
  });

  // File input change handlers
  codebaseInput.addEventListener('change', function(e) {
    if (e.target.files.length > 0) {
      codebaseFile = e.target.files[0];
      codebaseFileName.textContent = codebaseFile.name;
      codebaseFileName.classList.remove('d-none');
      updateSubmitButton();
    }
  });

  docsInput.addEventListener('change', function(e) {
    if (e.target.files.length > 0) {
      docsFile = e.target.files[0];
      docsFileName.textContent = docsFile.name;
      docsFileName.classList.remove('d-none');
      updateSubmitButton();
    }
  });

  // Submit handler
  submitBtn.addEventListener('click', async function(e) {
    e.preventDefault();

    if (!codebaseFile) {
      alert('Please upload a codebase ZIP file');
      return;
    }

    const formData = new FormData();
    formData.append('codebase', codebaseFile);
    if (docsFile) {
      formData.append('docs', docsFile);
    }
    formData.append('notes', document.getElementById('submissionNotes').value);

    submitBtn.disabled = true;
    reviewingCard.classList.remove('d-none');

    try {
      // Simulate review delay
      await new Promise(resolve => setTimeout(resolve, 2000));

      reviewingCard.classList.add('d-none');
      submitBtn.disabled = false;

      // Navigate to viva
      window.location.href = '/viva';
    } catch (error) {
      console.error('Submission error:', error);
      alert('Error submitting codebase. Please try again.');
      reviewingCard.classList.add('d-none');
      submitBtn.disabled = false;
    }
  });

  function updateSubmitButton() {
    submitBtn.disabled = !codebaseFile;
  }

  function setupDropzone(dropzone, input, onFilePicked) {
    dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.style.borderColor = '#0d6efd';
      dropzone.style.backgroundColor = '#f0f8ff';
    });

    dropzone.addEventListener('dragleave', () => {
      dropzone.style.borderColor = '#dee2e6';
      dropzone.style.backgroundColor = 'transparent';
    });

    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.style.borderColor = '#dee2e6';
      dropzone.style.backgroundColor = 'transparent';

      const files = e.dataTransfer.files;
      if (files.length > 0) {
        onFilePicked(files[0]);
      }
    });

    dropzone.addEventListener('click', () => {
      input.click();
    });
  }
});
