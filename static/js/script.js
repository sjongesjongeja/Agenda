/**
 * Agenda Web App - Client-Side Enhancements
 * Pure Vanilla JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
    // ------------------------------------------------------------------------
    // Flash message close buttons
    // ------------------------------------------------------------------------
    document.querySelectorAll('.alert-close').forEach(btn => {
        btn.addEventListener('click', () => {
            const alert = btn.closest('.alert');
            if (alert) {
                alert.style.opacity = '0';
                alert.style.transform = 'translateY(-10px)';
                setTimeout(() => alert.remove(), 200);
            }
        });
    });

    // ------------------------------------------------------------------------
    // Delete Confirmation Handling
    // ------------------------------------------------------------------------
    document.querySelectorAll('form.delete-event-form').forEach(form => {
        form.addEventListener('submit', (e) => {
            const title = form.getAttribute('data-event-title') || 'deze afspraak';
            const confirmed = window.confirm(`Weet je zeker dat je "${title}" definitief wilt verwijderen?`);
            if (!confirmed) {
                e.preventDefault();
            }
        });
    });

    // ------------------------------------------------------------------------
    // Quick Event Detail Modal
    // ------------------------------------------------------------------------
    const modalOverlay = document.getElementById('event-modal');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    const modalTitle = document.getElementById('modal-title');
    const modalDate = document.getElementById('modal-date');
    const modalTime = document.getElementById('modal-time');
    const modalLocation = document.getElementById('modal-location');
    const modalDescription = document.getElementById('modal-description');
    const modalEditBtn = document.getElementById('modal-edit-btn');
    const modalDeleteForm = document.getElementById('modal-delete-form');
    const modalLocationWrapper = document.getElementById('modal-location-wrapper');
    const modalDescWrapper = document.getElementById('modal-desc-wrapper');

    function closeModal() {
        if (modalOverlay) {
            modalOverlay.classList.remove('is-active');
            modalOverlay.setAttribute('aria-hidden', 'true');
        }
    }

    if (modalCloseBtn) {
        modalCloseBtn.addEventListener('click', closeModal);
    }

    if (modalOverlay) {
        modalOverlay.addEventListener('click', (e) => {
            if (e.target === modalOverlay) {
                closeModal();
            }
        });
    }

    // Attach click handlers to event pills for quick modal preview
    document.querySelectorAll('[data-event-id]').forEach(elem => {
        elem.addEventListener('click', (e) => {
            // If modifier key or middle click, allow default browser navigation
            if (e.metaKey || e.ctrlKey || e.shiftKey || e.button === 1) return;

            // Only hijack if modal element exists
            if (!modalOverlay) return;

            e.preventDefault();
            e.stopPropagation();

            const eventId = elem.getAttribute('data-event-id');
            if (!eventId) return;

            // Fetch event data as JSON
            fetch(`/event/${eventId}?format=json`, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
            .then(res => {
                if (!res.ok) throw new Error('Network response was not ok');
                return res.json();
            })
            .then(data => {
                if (modalTitle) modalTitle.textContent = data.title;
                if (modalDate) modalDate.textContent = data.formatted_date || data.event_date;
                
                let timeStr = data.start_time || '';
                if (data.start_time && data.end_time) {
                    timeStr += ` - ${data.end_time}`;
                } else if (!data.start_time) {
                    timeStr = 'Hele dag';
                }
                if (modalTime) modalTime.textContent = timeStr;

                if (modalLocation && modalLocationWrapper) {
                    if (data.location) {
                        modalLocation.textContent = data.location;
                        modalLocationWrapper.style.display = 'flex';
                    } else {
                        modalLocationWrapper.style.display = 'none';
                    }
                }

                if (modalDescription && modalDescWrapper) {
                    if (data.description) {
                        modalDescription.textContent = data.description;
                        modalDescWrapper.style.display = 'flex';
                    } else {
                        modalDescWrapper.style.display = 'none';
                    }
                }

                if (modalEditBtn) {
                    modalEditBtn.href = `/edit/${data.id}`;
                }

                if (modalDeleteForm) {
                    modalDeleteForm.action = `/delete/${data.id}`;
                    modalDeleteForm.setAttribute('data-event-title', data.title);
                }

                modalOverlay.classList.add('is-active');
                modalOverlay.setAttribute('aria-hidden', 'false');
            })
            .catch(err => {
                console.error('Error fetching event details:', err);
                // Fallback: navigate directly to event detail page
                window.location.href = `/event/${eventId}`;
            });
        });
    });

    // ------------------------------------------------------------------------
    // Keyboard navigation
    // ------------------------------------------------------------------------
    document.addEventListener('keydown', (e) => {
        // Escape closes modal
        if (e.key === 'Escape') {
            closeModal();
            return;
        }

        // Avoid shortcuts if typing in input/textarea
        if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
            return;
        }

        // Quick shortcut to focus search with '/'
        if (e.key === '/') {
            const searchInput = document.querySelector('.search-input');
            if (searchInput) {
                e.preventDefault();
                searchInput.focus();
            }
        }
    });
});
