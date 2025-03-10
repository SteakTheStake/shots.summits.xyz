function fetchNewComments(screenshotId) {
    fetch(`/get_comments/${screenshotId}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const commentsSection = document.querySelector(`#imageModal-${screenshotId} .comments-section`);
                commentsSection.innerHTML = ''; // Clear existing comments

                data.comments.forEach(comment => {
                    const newComment = document.createElement('div');
                    newComment.classList.add('single-comment', 'mb-3', 'p-2', 'comment-background');
                    newComment.innerHTML = `
                        <div class="comment-rank-${comment.user_rank.toLowerCase()}">
                            [${comment.user_rank}] <strong>${comment.username}</strong> » <span class="comment-message">${comment.comment_text}</span>
                        </div>
                        <small class="comment-subtle-text">${comment.created_at}</small>
                    `;
                    commentsSection.appendChild(newComment);
                });
            }
        })
        .catch(error => console.error('Error fetching comments:', error));
}

// Poll for new comments every 5 seconds
setInterval(() => {
    const screenshotId = document.querySelector('.comment-form')?.getAttribute('data-screenshot-id');
    if (screenshotId) {
        fetchNewComments(screenshotId);
    }
}, 5000);

document.addEventListener('DOMContentLoaded', function () {
    // Handle comment form submission
    document.querySelectorAll('.comment-form').forEach(form => {
        form.addEventListener('submit', function (event) {
            event.preventDefault(); // Prevent the default form submission

            const formData = new FormData(this);
            const screenshotId = this.getAttribute('data-screenshot-id');

            fetch(`/comment/${screenshotId}`, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest' // Identify the request as AJAX
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Append the new comment to the comments section
                    const commentsSection = this.closest('.modal-body').querySelector('.comments-section');
                    const newComment = document.createElement('div');
                    newComment.classList.add('single-comment', 'mb-3', 'p-2', 'comment-background');
                    newComment.innerHTML = `
                        <div class="comment-rank-${data.comment.user_rank.toLowerCase()}">
                            [${data.comment.user_rank}] <strong>${data.comment.username}</strong> » <span class="comment-message">${data.comment.comment_text}</span>
                        </div>
                        <small class="comment-subtle-text">${data.comment.created_at}</small>
                    `;
                    commentsSection.prepend(newComment); // Add the new comment at the top

                    // Clear the comment textarea
                    this.querySelector('textarea').value = '';
                } else {
                    alert(data.message); // Show error message
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while posting the comment.');
            });
        });
    });
});

document.addEventListener('DOMContentLoaded', function () {
    // Share Button Functionality
    document.querySelectorAll('.share-button').forEach(button => {
        button.addEventListener('click', function () {
            const imageId = this.getAttribute('data-image-id');
            const username = this.getAttribute('data-username');
            const uniqueUrl = `${window.location.origin}/${username}/${imageId}`;

            // Copy to Clipboard
            navigator.clipboard.writeText(uniqueUrl).then(() => {
                alert('Link copied to clipboard: ' + uniqueUrl);
            }).catch(() => {
                alert('Failed to copy link. Please manually copy the URL.');
            });
        });
    });

    // Open Image in Modal
    document.querySelectorAll('.clickable-image').forEach(image => {
        image.addEventListener('click', function () {
            const imageId = this.getAttribute('data-image-id');
            const modal = document.getElementById(`imageModal-${imageId}`);
            if (modal) {
                $(modal).modal('show'); // Bootstrap modal show
            }
        });
    });
  
    // === Like/Unlike Feature ===
    document.querySelectorAll(".like-toggle").forEach(function(toggle) {
      toggle.addEventListener("click", function(e) {
        e.preventDefault();
        const screenshotId = toggle.getAttribute("data-screenshot-id");
  
        fetch(`/toggle_like/${screenshotId}`, {
          method: "POST",
          headers: {
            "X-Requested-With": "XMLHttpRequest"
          }
        })
        .then((response) => response.json())
        .then((data) => {
          console.log("toggle_like response", data);
          if (data.error) {
            alert(data.error);
            return;
          }
          const isLiked = (data.status === "liked");
          updateLikeToggle(toggle, isLiked, data.like_count);
        })
        .catch((err) => {
          console.error("Error toggling like:", err);
          alert("Could not toggle like. Please try again.");
        });
      });
    });
  
    function updateLikeToggle(toggle, isLiked, likeCount) {
      const img = toggle.querySelector("img");
      const likedUrl = toggle.getAttribute("data-liked-url");
      const likeUrl = toggle.getAttribute("data-like-url");
  
      // bust the cache
      const timestamp = new Date().getTime();
      if (isLiked) {
        img.src = likedUrl + "?t=" + timestamp;
        img.alt = "Unlike";
      } else {
        img.src = likeUrl + "?t=" + timestamp;
        img.alt = "Like";
      }
  
      const screenshotId = toggle.getAttribute("data-screenshot-id");
      const likeCountSpan = document.querySelector(
        `.like-count[data-screenshot-id="${screenshotId}"]`
      );
      if (likeCountSpan) {
        likeCountSpan.textContent = likeCount;
      }
    }
  
    // === Comment AJAX Submission and Enter Key Handling ===
    // Intercept comment form submission and send via AJAX
    document.body.addEventListener("submit", function (e) {
      const form = e.target;
      if (form.matches(".comment-form")) {
        e.preventDefault();
        const screenshotId = form.dataset.screenshotId;
        const formData = new FormData(form);
        fetch(form.action, {
          method: "POST",
          body: formData,
          headers: {
            "X-Requested-With": "XMLHttpRequest"
          }
        })
        .then(response => response.json())
        .then(data => {
          if (data.error) {
            alert(data.error);
            return;
          }
          const commentsModal = document.getElementById(`commentsModal-${screenshotId}`);
          if (commentsModal) {
            const commentsSection = commentsModal.querySelector(".comments-section");
            const noCommentsMsg = commentsSection.querySelector("p");
            if (noCommentsMsg && noCommentsMsg.textContent.includes("No comments yet.")) {
              noCommentsMsg.remove();
            }
            const newCommentDiv = document.createElement("div");
            newCommentDiv.classList.add("single-comment", "mb-3");
            newCommentDiv.innerHTML = `
              <strong class="comment-title-text">${data.comment.username}:</strong>
              <p class="comment-text">${data.comment.comment_text}</p>
              <small class="comment-subtle-text">${data.comment.created_at}</small>
            `;
            commentsSection.appendChild(newCommentDiv);
            const modalTitle = commentsModal.querySelector(".modal-title");
            if (modalTitle) {
              modalTitle.textContent = `Comments (${data.comment_count})`;
            }
          }
          // Clear the comment textarea
          form.querySelector("[name='comment_text']").value = "";
        })
        .catch(err => {
          console.error("Error posting comment:", err);
          alert("Something went wrong while posting the comment.");
        });
      }
    });
  
    // Allow SHIFT+ENTER for newline and ENTER (without shift) to submit comment
    document.body.addEventListener("keydown", function (e) {
      const textarea = e.target;
      if (textarea.matches(".comment-form textarea")) {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          textarea.closest("form").dispatchEvent(new Event("submit", { cancelable: true }));
        }
      }
    });
  });

  function formatLocalTime(utcTimestamp) {
    const date = new Date(utcTimestamp + ' UTC'); // Append 'UTC' to ensure parsing as UTC
    return date.toLocaleString(); // Convert to local time
}

// Example usage:
fetch(`/comment/${screenshotId}`, {
    method: 'POST',
    body: formData,
    headers: {
        'X-Requested-With': 'XMLHttpRequest'
    }
})
.then(response => response.json())
.then(data => {
    if (data.status === 'success') {
        const newComment = document.createElement('div');
        newComment.classList.add('single-comment', 'mb-3', 'p-2', 'comment-background');
        newComment.innerHTML = `
            <div class="comment-rank-${data.comment.user_rank.toLowerCase()}">
                [${data.comment.user_rank}] <strong>${data.comment.username}</strong> » <span class="comment-message">${data.comment.comment_text}</span>
            </div>
            <small class="comment-subtle-text">${formatLocalTime(data.comment.created_at)}</small>
        `;
        document.querySelector('.comments-section').prepend(newComment);
    } else {
        alert(data.error);
    }
})
.catch(error => console.error('Error:', error));

document.querySelectorAll('.btn-report').forEach(button => {
  button.addEventListener('click', function() {
      const filename = this.dataset.imageFilename;
      const imageUrl = `${window.location.origin}/uploads/${filename}`;
      navigator.clipboard.writeText(imageUrl)
          .then(() => {
              // Optional: Show a toast or alert instead of a generic alert
              alert('Image URL copied to clipboard!');
          })
          .catch(err => {
              console.error('Failed to copy URL:', err);
          });
  });
});