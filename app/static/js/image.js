document.addEventListener("DOMContentLoaded", function () {
    // Filtering functionality
    const filterToggles = document.querySelectorAll(".filter-checkbox input");
    const gridItems = document.querySelectorAll(".grid-item");
    const lightbox = document.querySelector(".lightbox");
    const lightboxImg = lightbox.querySelector("img");
    let currentImageIndex = 0;
    let visibleImages = []; // Track currently visible images for filtering

    // Update visible images when filters change
    function updateFilters() {
        const activeUserFilters = Array.from(document.querySelectorAll('[data-filter="user"]:checked')).map((checkbox) => checkbox.value);

        const activeTagFilters = Array.from(document.querySelectorAll('[data-filter="tag"]:checked')).map((checkbox) => checkbox.value);

        visibleImages = []; // Reset visible images array

        gridItems.forEach((item) => {
            const itemUser = item.dataset.user;
            const itemTags = item.dataset.tags.split(",").map((tag) => tag.trim());

            const userMatch = activeUserFilters.length === 0 || activeUserFilters.includes(itemUser);
            const tagMatch = activeTagFilters.length === 0 || activeTagFilters.some((tag) => itemTags.includes(tag));

            if (userMatch && tagMatch) {
                item.style.display = "";
                visibleImages.push(item.querySelector("img"));
            } else {
                item.style.display = "none";
            }
        });
    }

    // Initialize lightbox functionality
    function initLightbox() {
        const allImages = document.querySelectorAll(".grid-item img");
        const lightbox = document.querySelector(".lightbox");
        const lightboxImg = lightbox.querySelector("img");
        const lightboxInfo = lightbox.querySelector(".lightbox-info");
        let currentImageIndex = 0;
      
        // A helper function to update .lightbox-info based on the current index
        function updateLightboxInfo(index) {
          if (index < 0 || index >= visibleImages.length) return;
      
          // The <img> element for the current index
          const currentImg = visibleImages[index];
      
          // Find its .grid-item parent
          const parentItem = currentImg.closest(".grid-item");
          if (!parentItem) return;
      
          // Read data attributes
          const user = parentItem.dataset.user || "Unknown User";
          const date = parentItem.dataset.date || "Unknown Date";
          const group = parentItem.dataset.group || "";
          const rawTags = parentItem.dataset.tags || "";
      
          // Build your HTML snippet
          const tagList = rawTags.split(",").map(t => t.trim()).filter(Boolean);
      
          let infoHTML = `<p><strong>Uploaded By:</strong> ${user}</p>`;
          if (group) {
            infoHTML += `<p><strong>Group:</strong> ${group}</p>`;
          }
          infoHTML += `<p><strong>Date:</strong> ${date}</p>`;
      
          if (tagList.length > 0) {
            infoHTML += `<div class="tag-section"><strong>Tags:</strong> `;
            tagList.forEach(tag => {
              infoHTML += `<span class="tag-badge">#${tag}</span> `;
            });
            infoHTML += `</div>`;
          }
      
          // Insert into .lightbox-info
          lightboxInfo.innerHTML = infoHTML;
        }
      
        // When user clicks an image
        allImages.forEach((img) => {
          img.addEventListener("click", () => {
            currentImageIndex = visibleImages.indexOf(img);
            if (currentImageIndex !== -1) {
              // Show the lightbox
              lightboxImg.src = img.src;
              lightbox.classList.add("active");
              document.body.style.overflow = "hidden";
      
              // Populate info for this index
              updateLightboxInfo(currentImageIndex);
            }
          });
        });
      
        // Close lightbox
        lightbox.querySelector(".close-lightbox").addEventListener("click", () => {
          lightbox.classList.remove("active");
          document.body.style.overflow = "";
        });
      
        // Close on background click
        lightbox.addEventListener("click", (e) => {
          if (e.target === lightbox) {
            lightbox.classList.remove("active");
            document.body.style.overflow = "";
          }
        });
      
        // Previous image
        lightbox.querySelector(".lightbox-prev").addEventListener("click", (e) => {
          e.stopPropagation();
          if (visibleImages.length > 0) {
            currentImageIndex = (currentImageIndex - 1 + visibleImages.length) % visibleImages.length;
            lightboxImg.src = visibleImages[currentImageIndex].src;
            updateLightboxInfo(currentImageIndex); // <--- Update info
          }
        });
      
        // Next image
        lightbox.querySelector(".lightbox-next").addEventListener("click", (e) => {
          e.stopPropagation();
          if (visibleImages.length > 0) {
            currentImageIndex = (currentImageIndex + 1) % visibleImages.length;
            lightboxImg.src = visibleImages[currentImageIndex].src;
            updateLightboxInfo(currentImageIndex); // <--- Update info
          }
        });
      
        // Keyboard navigation
        document.addEventListener("keydown", (e) => {
          if (!lightbox.classList.contains("active")) return;
      
          switch (e.key) {
            case "Escape":
              lightbox.classList.remove("active");
              document.body.style.overflow = "";
              break;
            case "ArrowLeft":
              if (visibleImages.length > 0) {
                currentImageIndex = (currentImageIndex - 1 + visibleImages.length) % visibleImages.length;
                lightboxImg.src = visibleImages[currentImageIndex].src;
                updateLightboxInfo(currentImageIndex);
              }
              break;
            case "ArrowRight":
              if (visibleImages.length > 0) {
                currentImageIndex = (currentImageIndex + 1) % visibleImages.length;
                lightboxImg.src = visibleImages[currentImageIndex].src;
                updateLightboxInfo(currentImageIndex);
              }
              break;
          }
        });
      }      

    // Initialize everything
    filterToggles.forEach((toggle) => {
        toggle.addEventListener("change", updateFilters);
    });

    // Toggle filter menu
    document.querySelector(".filter-toggle").addEventListener("click", function () {
        const filterDropdowns = document.querySelectorAll(".filter-dropdown");
        filterDropdowns.forEach((dropdown) => {
            dropdown.classList.toggle("show");
        });
    });

    // Initial setup
    updateFilters(); // Initialize visible images array
    initLightbox(); // Setup lightbox functionality
});

const mobileMenu = document.querySelector('.links-container_mobile');
const menuToggle = document.querySelector('.burger'); // Replace with your button selector

function toggleMenu() {
  if (mobileMenu.classList.contains('show')) {
    // Start closing animation
    mobileMenu.classList.remove('show');
    mobileMenu.classList.add('hiding');
    
    // After animation completes, remove classes and hide
    mobileMenu.addEventListener('animationend', function handler() {
      mobileMenu.classList.remove('hiding');
      mobileMenu.style.display = 'none';
      mobileMenu.removeEventListener('animationend', handler);
    }, { once: true });
  } else {
    // Open menu
    mobileMenu.style.display = 'flex';
    mobileMenu.classList.add('show');
  }
}

// Add click event to your hamburger button
menuToggle.addEventListener('click', toggleMenu);

// Add click event to close when clicking a link (optional)
mobileMenu.querySelectorAll('a').forEach(link => {
  link.addEventListener('click', toggleMenu);
});