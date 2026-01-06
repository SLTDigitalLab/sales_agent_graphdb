import { Helmet } from 'react-helmet-async';

export default function SEO({ title, description, name = 'AI Enterprise Agent' }) {
  return (
    <Helmet>
      {/* Browser Tab Title */}
      <title>{title} | {name}</title>
      <meta name='description' content={description} />
      
      {/* Social Media Preview (Open Graph) */}
      <meta property="og:type" content="website" />
      <meta property="og:title" content={title} />
      <meta property="og:description" content={description} />
      
      {/* Twitter Card */}
      <meta name="twitter:creator" content={name} />
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={title} />
      <meta name="twitter:description" content={description} />
    </Helmet>
  );
}