// Utility Functions
function validateEmail(email) {
    if (!email) {
        return { isValid: false, message: 'Email is required' };
    }
    
    // Comprehensive email validation regex
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!emailRegex.test(email)) {
        return { isValid: false, message: 'Invalid email format' };
    }
    
    // Check for common disposable email domains
    const disposableDomains = [
        'tempmail.com', 'throwaway.com', 'guerrillamail.com', 
        'mailinator.com', 'temp-mail.org', '10minutemail.com',
        'yopmail.com', 'sharklasers.com', 'guerrillamail.net',
        'spam4.me', 'emailtemporar.com', 'dispostable.com'
    ];
    
    try {
        const domain = email.split('@')[1].toLowerCase();
        if (disposableDomains.includes(domain)) {
            return { isValid: false, message: 'Disposable email addresses are not allowed' };
        }
    } catch (error) {
        return { isValid: false, message: 'Invalid email format' };
    }
    
    return { isValid: true, message: '' };
}

function validatePassword(password) {
    // Enhanced password validation
    const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;
    return {
        isValid: passwordRegex.test(password),
        message: 'Password must be at least 8 characters long, include uppercase and lowercase letters, a number, and a special character'
    };
}

function validatePasswordMatch(password, confirmPassword) {
    return password === confirmPassword;
}

// Error display function
function showError(message, containerId = 'loginErrorContainer') {
    const errorContainer = document.getElementById(containerId);
    if (errorContainer) {
        // Remove any existing error messages
        errorContainer.innerHTML = '';
        
        // Create error message element
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-error';
        errorDiv.textContent = message;
        
        // Insert new error message
        errorContainer.appendChild(errorDiv);

        // Auto-hide after 3 seconds
        setTimeout(() => {
            errorDiv.classList.add('fade-out');
            setTimeout(() => {
                errorDiv.remove();
            }, 300);
        }, 5000);
    }
}

// Password toggle functionality
function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;

    const toggleButton = input.parentElement.querySelector('.toggle-password');
    if (!toggleButton) return;

    const icon = toggleButton.querySelector('i');
    if (!icon) return;

    // Toggle password visibility
    const currentType = input.getAttribute('type');
    const newType = currentType === 'password' ? 'text' : 'password';
    input.setAttribute('type', newType);
    
    // Update icon
    const iconClass = newType === 'password' ? 'fa-eye' : 'fa-eye-slash';
    icon.classList.remove('fa-eye', 'fa-eye-slash');
    icon.classList.add(iconClass);

    // Add visual feedback
    input.classList.add('transition-type');
    setTimeout(() => input.classList.remove('transition-type'), 200);
}

// Initialize auth
document.addEventListener('DOMContentLoaded', function() {
    initAuth();
});

// Initialize auth functions
function initAuth() {
    initLoginForm();
    initSignupForm();
    initPasswordReset();
    
    // Initialize password toggle buttons
    const passwordInputs = document.querySelectorAll('.form-input[type="password"]');
    passwordInputs.forEach(input => {
        const toggleButton = input.parentElement.querySelector('.toggle-password');
        if (toggleButton) {
            toggleButton.onclick = () => togglePassword(input.id);
        }
    });
}

// Initialize login form
function initLoginForm() {
    const loginForm = document.getElementById('loginForm');
    if (!loginForm) return;

    loginForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const email = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPassword').value;
        
        // Validate email
        const emailValidation = validateEmail(email);
        if (!emailValidation.isValid) {
            showError(emailValidation.message);
            return;
        }

        // Validate password
        const passwordValidation = validatePassword(password);
        if (!passwordValidation.isValid) {
            showError(passwordValidation.message);
            return;
        }

        // Submit form
        loginForm.submit();
    });
}

// Initialize signup form
function initSignupForm() {
    const signupForm = document.getElementById('signupForm');
    if (!signupForm) return;

    signupForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const fullName = document.getElementById('signupFullName').value;
        const email = document.getElementById('signupEmail').value;
        const password = document.getElementById('signupPassword').value;
        const confirmPassword = document.getElementById('signupConfirmPassword').value;
        const terms = document.getElementById('terms').checked;
        
        // Validate full name
        if (!fullName.trim()) {
            showError('Please enter your full name');
            return;
        }

        // Validate email
        const emailValidation = validateEmail(email);
        if (!emailValidation.isValid) {
            showError(emailValidation.message);
            return;
        }

        // Validate password
        const passwordValidation = validatePassword(password);
        if (!passwordValidation.isValid) {
            showError(passwordValidation.message);
            return;
        }

        // Validate password match
        if (password !== confirmPassword) {
            showError('Passwords do not match');
            return;
        }

        // Validate terms acceptance
        if (!terms) {
            showError('Please accept the Terms and Conditions');
            return;
        }

        // Submit form
        signupForm.submit();
            return response.json().then(data => {
                if (response.ok) {
                    // Successful registration
                    window.location.href = data.redirect || '/login';
                } else {
                    // Server returned an error
                    if (data.errors) {
                        Object.keys(data.errors).forEach(key => {
                            showError(data.errors[key], 'signupErrorContainer');
                        });
                    } else {
                        throw new Error(data.error || 'Registration failed');
                    }
                }
            });
        })
        .catch(error => {
            showError(error.message || 'An error occurred during registration', 'signupErrorContainer');
        });
}

// Password reset form handling
function handleResetPasswordForm() {
    const resetForm = document.getElementById('resetPasswordForm');
    if (!resetForm) return;

    resetForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirm_password').value;
        
        // Client-side validation
        if (!password || !confirmPassword) {
            showError('Please enter both password fields');
            return;
        }

        const passwordValidation = validatePassword(password);
        if (!passwordValidation.isValid) {
            showError(passwordValidation.message);
            return;
        }

        // Validate password match
        if (password !== confirmPassword) {
            showError('Passwords do not match');
            return;
        }

        // Submit form
        resetForm.submit();
    });
}

// Initialize flash message auto-dismiss
const flashMessages = document.querySelectorAll('.alert');
flashMessages.forEach(message => {
    setTimeout(() => {
        message.classList.add('fade-out');
        setTimeout(() => {
            message.remove();
        }, 300);
    }, 5000);
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', initAuth);