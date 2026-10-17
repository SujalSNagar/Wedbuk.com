
document.addEventListener("DOMContentLoaded", () => {
    const slider = document.getElementById("advancePercentage");
    const percentageLabel = document.getElementById("advancePercentageLabel");
    const totalLabel = document.getElementById("totalAmountLabel");
    const payNowLabel = document.getElementById("payNowLabel");
    const remainingLabel = document.getElementById("remainingAmountLabel");
    const payButton = document.getElementById("payButton");
    const payButtonLabel = document.getElementById("payButtonLabel");

    if (!slider || !payButton) {
        console.error("Payment slider or button was not found.");
        return;
    }

    const config = payButton.dataset;
    const total = parseFloat(
        (totalLabel?.textContent || "0").replace(/[₹,\s]/g, "")
    );

    if (!Number.isFinite(total) || total <= 0) {
        console.error("Invalid booking total.");
        payButton.disabled = true;
        return;
    }

    let paymentInProgress = false;

    const money = (value) =>
        new Intl.NumberFormat("en-IN", {
            style: "currency",
            currency: "INR",
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(value);

    function calculatePayment() {
        let percentage = Number(slider.value);

        // Allow only 20% to 100%, in steps of 5%.
        percentage = Math.max(20, Math.min(100, percentage));
        percentage = 20 + Math.round((percentage - 20) / 5) * 5;
        slider.value = String(percentage);

        // Calculate in paise to avoid floating-point rounding errors.
        const totalPaise = Math.round(total * 100);
        const payPaise = Math.round(totalPaise * percentage / 100);
        const remainingPaise = totalPaise - payPaise;

        const payAmount = payPaise / 100;
        const remainingAmount = remainingPaise / 100;

        if (percentageLabel) {
            percentageLabel.textContent = percentage;
        }

        if (totalLabel) {
            totalLabel.textContent = money(totalPaise / 100);
        }

        if (payNowLabel) {
            payNowLabel.textContent = money(payAmount);
        }

        if (remainingLabel) {
            remainingLabel.textContent = money(remainingAmount);
        }

        if (payButtonLabel) {
            payButtonLabel.textContent = `Pay ${money(payAmount)}`;
        }

        return { percentage, payAmount, remainingAmount };
    }

    slider.min = "20";
    slider.max = "100";
    slider.step = "5";
    slider.value = "20";

    slider.addEventListener("input", calculatePayment);
    slider.addEventListener("change", calculatePayment);

    calculatePayment();

    async function postForm(url, values) {
        const body = new FormData();

        body.append("csrfmiddlewaretoken", config.csrfToken || "");

        Object.entries(values).forEach(([key, value]) => {
            body.append(key, String(value));
        });

        const response = await fetch(url, {
            method: "POST",
            body,
            credentials: "same-origin",
            headers: {
                "X-Requested-With": "XMLHttpRequest"
            }
        });

        const data = await response.json().catch(() => ({}));

        if (!response.ok || !data.success) {
            throw new Error(data.message || "Payment request failed.");
        }

        return data;
    }

    payButton.addEventListener("click", async () => {
        if (paymentInProgress) return;

        if (typeof window.Razorpay !== "function") {
            alert("Payment gateway could not load. Please refresh and retry.");
            return;
        }

        paymentInProgress = true;
        payButton.disabled = true;
        payButton.classList.add("is-loading");

        try {
            const selected = calculatePayment();

            // The server calculates the amount again and creates
            // a Razorpay order for this exact percentage.
            const order = await postForm(config.createOrderUrl, {
                percentage: selected.percentage
            });

            const options = {
                key: config.key,
                amount: order.amount_paise,
                currency: "INR",
                name: "WedBook",
                description: config.description || "Booking payment",
                order_id: order.order_id,
                prefill: {
                    name: config.customerName || "",
                    email: config.customerEmail || "",
                    contact: config.customerPhone || ""
                },
                theme: {
                    color: "#8e1b32"
                },
                handler: async (response) => {
                    try {
                        const result = await postForm(config.verifyUrl, {
                            razorpay_order_id: response.razorpay_order_id,
                            razorpay_payment_id: response.razorpay_payment_id,
                            razorpay_signature: response.razorpay_signature
                        });

                        window.location.href = result.redirect_url;
                    } catch (error) {
                        alert(
                            error.message ||
                            "Payment verification failed. Please contact support if money was deducted."
                        );
                        paymentInProgress = false;
                        payButton.disabled = false;
                        payButton.classList.remove("is-loading");
                    }
                },
                modal: {
                    ondismiss: () => {
                        paymentInProgress = false;
                        payButton.disabled = false;
                        payButton.classList.remove("is-loading");
                    }
                }
            };

            const razorpay = new window.Razorpay(options);

            razorpay.on("payment.failed", (event) => {
                console.error("Razorpay payment failed:", event.error);
                alert(
                    event.error?.description ||
                    "Payment failed. Please try again."
                );

                paymentInProgress = false;
                payButton.disabled = false;
                payButton.classList.remove("is-loading");
            });

            razorpay.open();
        } catch (error) {
            console.error("Unable to start payment:", error);
            alert(error.message || "Could not start payment. Please retry.");
            paymentInProgress = false;
            payButton.disabled = false;
            payButton.classList.remove("is-loading");
        }
    });
});
