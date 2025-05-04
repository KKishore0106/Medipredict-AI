class FlashMessage {
    constructor(element) {
        this.element = element;
        this.init();
    }

    init() {
        this.setupCloseButton();
        this.setupAutoHide();
        this.setupAnimation();
    }

    setupCloseButton() {
        const closeButton = this.element.querySelector('.close-flash');
        if (closeButton) {
            closeButton.addEventListener('click', (e) => {
                e.stopPropagation();
                this.hide();
            });
            
            // Add hover effect
            closeButton.addEventListener('mouseenter', () => {
                closeButton.style.transform = 'scale(1.2)';
            });
            
            closeButton.addEventListener('mouseleave', () => {
                closeButton.style.transform = 'scale(1)';
            });
        }
    }

    setupAutoHide() {
        // Auto-hide after 5 seconds
        setTimeout(() => {
            this.hide();
        }, 5000);
    }

    setupAnimation() {
        // Add show class to trigger animation
        this.element.classList.add('show');
        
        // Add hover effect
        this.element.addEventListener('mouseenter', () => {
            this.element.style.transform = 'translateX(0) scale(1.02)';
        });
        
        this.element.addEventListener('mouseleave', () => {
            this.element.style.transform = 'translateX(0)';
        });
    }

    hide() {
        // Add fade-out class
        this.element.classList.add('fade-out');
        
        // Wait for animation to complete
        setTimeout(() => {
            // Remove the element from DOM
            this.element.remove();
        }, 300); // Match the transition duration
    }
}

// Initialize all flash messages when page loads
document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        new FlashMessage(message);
    });
});
