const puppeteer = require('puppeteer');
(async () => {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    page.on('pageerror', err => {
        console.log('Page error: ', err.toString());
    });
    page.on('error', err => {
        console.log('Error: ', err.toString());
    });
    await page.goto('http://localhost:8000/dashboard', {waitUntil: 'networkidle0'});
    await browser.close();
})();
