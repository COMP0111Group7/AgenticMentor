document.addEventListener('DOMContentLoaded', function() {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const fileName = document.getElementById('fileName');
  const analyzingCard = document.getElementById('analyzingCard');
  const continueBtn = document.getElementById('continueBtn');
  const referencesCard = document.getElementById('referencesCard');
  const referencesList = document.getElementById('referencesList');

  let selectedFile = null;

  // File input change handler
  fileInput.addEventListener('change', function(e) {
    if (e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  });

  // Dropzone handlers
  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.style.borderColor = '#0d6efd';
    dropzone.style.backgroundColor = '#f0f8ff';
  });

  dropzone.addEventListener('dragleave', () => {
    dropzone.style.borderColor = '#d3d0c6';
    dropzone.style.backgroundColor = 'transparent';
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.style.borderColor = '#d3d0c6';
    dropzone.style.backgroundColor = 'transparent';

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelected(files[0]);
    }
  });

  // Dropzone click handler (only trigger if not clicking the label)
  dropzone.addEventListener('click', (e) => {
    if (e.target.tagName !== 'LABEL' && !e.target.closest('label')) {
      fileInput.click();
    }
  });

  // Continue button handler
  continueBtn.addEventListener('click', () => {
    window.location.href = '/build';
  });

  function handleFileSelected(file) {
    selectedFile = file;
    
    // Show file name
    fileName.textContent = file.name;
    fileName.classList.remove('d-none');
    
    // Show analyzing card and hide dropzone interaction
    analyzingCard.classList.remove('d-none');
    dropzone.style.pointerEvents = 'none';
    dropzone.style.opacity = '0.6';
    
    // Simulate ingestion agent processing (2 seconds)
    setTimeout(() => {
      // Show continue button
      continueBtn.classList.remove('d-none');
      
      // Populate references from web search
      populateReferences();
    }, 2000);
  }

  function populateReferences() {
    // Sample references data - in production this would come from the backend
    const references = [
      {
        title: 'Python Best Practices for Web Development',
        url: 'https://docs.python.org/3/library/',
        source: 'Python Official Docs'
      },
      {
        title: 'REST API Design Guidelines',
        url: 'https://restfulapi.net/best-practices/',
        source: 'RESTful API'
      },
      {
        title: 'Database Optimization Techniques',
        url: 'https://www.postgresql.org/docs/',
        source: 'PostgreSQL Docs'
      },
      {
        title: 'Frontend Framework Comparison',
        url: 'https://developer.mozilla.org/en-US/',
        source: 'MDN Web Docs'
      },
      {
        title: 'Testing Strategies and Best Practices',
        url: 'https://testing-library.com/',
        source: 'Testing Library'
      }
    ];

    // Clear existing references
    referencesList.innerHTML = '';
    
    // Add references to the list
    references.forEach((ref, index) => {
      const refItem = document.createElement('a');
      refItem.href = ref.url;
      refItem.target = '_blank';
      refItem.rel = 'noopener noreferrer';
      refItem.className = 'am-reference-item';
      refItem.innerHTML = `
        <div class="am-reference-content">
          <p class="am-reference-title">${ref.title}</p>
          <p class="am-reference-source">${ref.source}</p>
        </div>
        <i class="ti ti-external-link"></i>
      `;
      referencesList.appendChild(refItem);
    });
    
    // Show references card
    referencesCard.classList.remove('d-none');
  }
});

