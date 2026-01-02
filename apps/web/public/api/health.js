// Health check endpoint for Next.js
module.exports = (req, res) => {
  res.status(200).json({ status: 'ok' });
};
